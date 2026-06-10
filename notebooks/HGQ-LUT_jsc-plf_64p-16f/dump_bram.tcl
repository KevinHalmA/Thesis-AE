# dump_bram.tcl
#
# Open a post-route DCP and dump every RAMB18/RAMB36/FIFO cell with the
# properties we care about for the BRAM-vs-lookup_table_block analysis.
# Output is a single CSV-ish file consumed by the python analytics.
#
# Usage:
#   vivado -mode batch -source dump_bram.tcl -tclargs <dcp_path> <out_path>
#
# Output format (one record per cell, terminated by a blank line):
#   CELL|<hier_name>|<ref_name>|RAM_MODE=<mode>|RWA=<n>|RWB=<n>|WWA=<n>|WWB=<n>|DOA_REG=<x>|DOB_REG=<x>|LOC=<bel>
#   INIT|INIT_00|<256-hex-digits>
#   INIT|INIT_01|<256-hex-digits>
#   ...
#   INITP|INITP_00|<64-hex-digits>
#   ...
#   <blank line>
#
# Cell hierarchical names retain the original Verilog hierarchy
# (`stage<N>/op_<NN>/readout_reg`) so the python side can map each cell
# back to its source `lookup_table_block` instance directly. INIT/INITP
# blobs are also dumped as a fallback for cases where the name regex
# doesn't apply (e.g. depth-stacking, custom transforms).

if {[llength $argv] < 2} {
    puts "ERROR: usage: vivado -mode batch -source dump_bram.tcl -tclargs <dcp> <out>"
    exit 1
}

set dcp_path [lindex $argv 0]
set out_path [lindex $argv 1]

puts "dump_bram.tcl: opening $dcp_path"
open_checkpoint $dcp_path

set fp [open $out_path w]
puts $fp "# dcp=$dcp_path"

# REF_NAME filter: covers RAMB18E2/RAMB36E2 and the rarer FIFO18E2/FIFO36E2.
# (PRIMITIVE_GROUP == BMEM was wrong for Vivado 2025.1 — the real value is BLOCKRAM.)
set rambs [get_cells -hierarchical -filter {REF_NAME =~ "RAMB*" || REF_NAME =~ "FIFO*"}]
puts "dump_bram.tcl: found [llength $rambs] BRAM cells"

foreach c $rambs {
    set ref   [get_property REF_NAME       $c]
    set rmode [get_property RAM_MODE        $c]
    set rwa   [get_property READ_WIDTH_A    $c]
    set rwb   [get_property READ_WIDTH_B    $c]
    set wwa   [get_property WRITE_WIDTH_A   $c]
    set wwb   [get_property WRITE_WIDTH_B   $c]
    set doar  [get_property DOA_REG         $c]
    set dobr  [get_property DOB_REG         $c]
    set loc   [get_property LOC             $c]

    # Detect dual-port packing: when Vivado merges two ROMs into one BRAM,
    # the secondary's data comes out on DOUTBDOUT (port B). Single-port ROMs
    # leave port B floating (no nets connected to any DOUTBDOUT bit).
    set dob_pins [get_pins -of_objects $c -filter {NAME =~ "*/DOUTBDOUT*" || NAME =~ "*/DOUTPBDOUTP*"}]
    set b_used 0
    set b_pin_first ""
    foreach p $dob_pins {
        set net [get_nets -of_objects $p]
        if {$net ne ""} { set b_used 1; if {$b_pin_first eq ""} { set b_pin_first $p }; break }
    }

    # If port B is used, capture one fanout net so the python side can name
    # the secondary lookup_table_block (the net name often references the
    # downstream stage, e.g. stage2_inp[1669] → stage2/op_521/...).
    set b_fanout_pin ""
    set b_fanout_net ""
    if {$b_used} {
        set net [get_nets -of_objects $b_pin_first]
        set b_fanout_net $net
        set fan [get_pins -of_objects $net -filter {DIRECTION == IN}]
        if {[llength $fan] > 0} { set b_fanout_pin [lindex $fan 0] }
    }

    puts $fp "CELL|$c|$ref|RAM_MODE=$rmode|RWA=$rwa|RWB=$rwb|WWA=$wwa|WWB=$wwb|DOA_REG=$doar|DOB_REG=$dobr|LOC=$loc|B_USED=$b_used|B_FANOUT_NET=$b_fanout_net|B_FANOUT_PIN=$b_fanout_pin"

    set props [list_property $c]
    foreach p $props {
        # Only capture INIT_<hh> / INITP_<hh> ROM-content slots (two hex digits),
        # skipping unrelated INIT_A / INIT_B / INIT_FILE properties.
        if {[regexp {^INIT_[0-9A-Fa-f][0-9A-Fa-f]$} $p]} {
            set v [get_property $p $c]
            puts $fp "INIT|$p|$v"
        } elseif {[regexp {^INITP_[0-9A-Fa-f][0-9A-Fa-f]$} $p]} {
            set v [get_property $p $c]
            puts $fp "INITP|$p|$v"
        }
    }

    puts $fp ""
}

close $fp
puts "dump_bram.tcl: wrote $out_path"
exit 0
