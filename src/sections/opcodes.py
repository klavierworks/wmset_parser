## LLM parsed, seems reasonable but needs review and close validation.

from typing import TypedDict

class Opcode(TypedDict):
    opcode: str
    hex: str
    description: str

OPCODES: dict[int, Opcode] = {

  # ── CONTROL FLOW ────────────────────────────────────────────────────────────

  -255: {
    "opcode": "IF",
    "hex": "0xFF01",
    "description": (
      "Begins a conditional block.  The next instruction(s) are evaluated as a "
      "condition.  Sets the interpreter state to 'condition mode' (v6=1)."
    ),
  },
  -252: {
    "opcode": "EXEC",
    "hex": "0xFF04",
    "description": (
      "Marks the start of an action (EXEC) block.  The instructions that follow "
      "are action opcodes to execute when the preceding condition passed.  Sets "
      "the interpreter state to 'exec mode' (v6=2, v4=3)."
    ),
  },
  -251: {
    "opcode": "ENDIF",
    "hex": "0xFF05",
    "description": (
      "Ends an IF/EXEC/ELSE block.  When reached in exec mode this terminates "
      "the current script and sub_54D7E0 returns 0."
    ),
  },
  -246: {
    "opcode": "IFBLOCK",
    "hex": "0xFF0A",
    "description": (
      "Explicitly begins an IF structure (v4=1).  Used to open a conditional "
      "block in the control-flow state machine."
    ),
  },
  -245: {
    "opcode": "ELSE",
    "hex": "0xFF0B",
    "description": (
      "ELSE clause.  When in IF-true state (v4=1) transitions to exec-true "
      "(v4=2); when in nested-true state (v4=4) transitions to exec nested "
      "(v4=3)."
    ),
  },
  -244: {
    "opcode": "NESTEDIF",
    "hex": "0xFF0C",
    "description": (
      "Nested IF inside an ELSE branch.  Valid from exec (v4=2) or nested-exec "
      "(v4=5) state; sets v4=4."
    ),
  },
  -243: {
    "opcode": "NESTEDELSE",
    "hex": "0xFF0D",
    "description": (
      "Nested ELSE inside an ELSE branch.  Valid from exec (v4=2) or nested-exec "
      "(v4=5) state; sets v4=6."
    ),
  },
  -242: {
    "opcode": "GOTO",
    "hex": "0xFF0E",
    "description": (
      "Unconditional jump.  param1+param2*256 = uint16 byte-offset from the "
      "start of the current script block (base pointer).  Interpreter jumps to "
      "that absolute offset within the section."
    ),
  },
  -234: {
    "opcode": "RETURN",
    "hex": "0xFF16",
    "description": (
      "Ends the current script entry-point.  When multi-entry scripts are in "
      "use the interpreter advances to the next entry; otherwise returns NULL "
      "(script finished, sub_54D7E0 returns 0)."
    ),
  },
  -235: {
    "opcode": "SET_RETURN_VALUE",
    "hex": "0xFF15",
    "description": (
      "Sets the return/output value for the script without stopping execution.  "
      "param1+param2*256 = uint16 value stored in the caller's out-variable.  "
      "Used in Section 11 (warp scripts) to communicate the warp-destination id "
      "back to sub_5484B0; a value of 3 triggers a special return path."
    ),
  },
  -248: {
    "opcode": "RETURN_WITH_VALUE",
    "hex": "0xFF08",
    "description": (
      "Terminates the script and returns code 1.  "
      "param1+param2*256 = uint16 output value written to the caller's "
      "out-variable.  sub_54D7E0 returns 1."
    ),
  },
  -213: {
    "opcode": "RETURN_WITH_CODE_3",
    "hex": "0xFF2B",
    "description": (
      "Terminates the script and returns code 3.  "
      "param1+param2*256 = uint16 output value written to the caller's "
      "out-variable.  sub_54D7E0 returns 3."
    ),
  },

  # ── CONDITION OPCODES  (used inside IF / IFBLOCK / NESTEDIF blocks) ─────────
  # All conditions return  1 (pass) or -1 (fail).
  # The interpreter skips to the ELSE/ENDIF on failure.

  -254: {
    "opcode": "LTEQ_THAN",
    "hex": "0xFF02",
    "description": (
      "Passes if (param1+param2*256) <= word_2036BDE.  word_2036BDE is a "
      "16-bit world-map state variable loaded from the save file at world-map "
      "init: SavemapVariables.unk5[12:13] (little-endian uint16 at save-game "
      "struct offset 0x100).  It lives in the same 32-byte block as the world "
      "type byte (unk5[22]) and vehicle type byte (unk5[24]), immediately "
      "before the MainStoryProgress field.  It represents a persistent "
      "scenario-phase counter that wmset scripts compare against to gate world "
      "map events and location access."
    ),
  },
  -253: {
    "opcode": "GREATER_THAN",
    "hex": "0xFF03",
    "description": (
      "Passes if (param1+param2*256) > word_2036BDE.  See LTEQ_THAN (-254) "
      "for the full description of word_2036BDE "
      "(SavemapVariables.unk5[12:13], save-game offset 0x100)."
    ),
  },
  -250: {
    "opcode": "CHECK_REGION_NUMBER",
    "hex": "0xFF06",
    "description": (
      "Passes if (param1+param2*256) == current world-map region number.  "
      "Region is computed via wm_GetRegionNumber(WORLD_MAP_COORD_X, WORLD_MAP_COORD_Y).  "
      "In 'tile mode' (dword_2040A30=1) compares against the tile-grid region "
      "index instead."
    ),
  },
  -249: {
    "opcode": "CHECK_TILE_POSITION",
    "hex": "0xFF07",
    "description": (
      "Passes if (param1+param2*256) == current tile index, where "
      "tile = tile_x + 128*tile_y.  Coordinates are derived from "
      "WORLD_MAP_COORD_X/Y with wrapping."
    ),
  },
  -247: {
    "opcode": "CHECK_VEHICLE_TYPE",
    "hex": "0xFF09",
    "description": (
      "Passes if the current vehicle/movement type matches param1+param2*256.  "
      "Known values: 33=bike, 48=Balamb Garden, 49=Shumi train, 50=Ragnarok, "
      "128=on foot, 129=any vehicle, 130=Galbadia aircraft, "
      "131=mobile Garden type, 132=special vehicle.  "
      "Fails immediately if dword_2040A2C (override flag) is set."
    ),
  },
  -241: {
    "opcode": "X_GREATER_THAN",
    "hex": "0xFF0F",
    "description": (
      "Passes if (param1+param2*256) > (WORLD_MAP_COORD_X & 0x1FFF).  "
      "In tile mode uses (dword_2040A24 % 4) << 11 instead."
    ),
  },
  -240: {
    "opcode": "Y_GREATER_THAN",
    "hex": "0xFF10",
    "description": (
      "Passes if (param1+param2*256) > (WORLD_MAP_COORD_Y & 0x1FFF).  "
      "In tile mode uses (dword_2040A28 % 4) << 11 instead."
    ),
  },
  -239: {
    "opcode": "X_LESS_THAN",
    "hex": "0xFF11",
    "description": (
      "Passes if (param1+param2*256) < (WORLD_MAP_COORD_X & 0x1FFF).  "
      "In tile mode uses (dword_2040A24 % 4) << 11 instead."
    ),
  },
  -238: {
    "opcode": "Y_LESS_THAN",
    "hex": "0xFF12",
    "description": (
      "Passes if (param1+param2*256) < (WORLD_MAP_COORD_Y & 0x1FFF).  "
      "In tile mode uses (dword_2040A28 % 4) << 11 instead."
    ),
  },
  -233: {
    "opcode": "CHECK_ENTITY_PROXIMITY",
    "hex": "0xFF17",
    "description": (
      "Passes if the nearest active entity whose id matches "
      "(param1+param2*256) is within sight/proximity of the player.  "
      "Searches the entity table (byte_20426D3/byte_20426E4) and performs a "
      "camera-space distance calculation."
    ),
  },
  -232: {
    "opcode": "CHECK_VEHICLE_ENTERING",
    "hex": "0xFF18",
    "description": (
      "Passes if vehicle param1+param2*256 is in its 'approaching / boarding "
      "start' state.  vehicle 50 (Ragnarok): byte_2036B70 == 6.  "
      "vehicle 48 (Balamb Garden): byte_2036B70 == 9."
    ),
  },
  -231: {
    "opcode": "CHECK_VEHICLE_BOARDED",
    "hex": "0xFF19",
    "description": (
      "Passes if vehicle param1+param2*256 is in its 'fully boarded / active' "
      "state.  vehicle 50 (Ragnarok): byte_2036B70 == 5.  "
      "vehicle 48 (Balamb Garden): byte_2036B70 == 8."
    ),
  },
  -230: {
    "opcode": "CHECK_CHARACTER_LOCATION",
    "hex": "0xFF1A",
    "description": (
      "Passes if the nearest NPC (dword_C75D0C) has location code "
      "(param1+param2*256).  Location code is read from byte_20426D0 array "
      "(entity table, offset 0)."
    ),
  },
  -229: {
    "opcode": "CHECK_CHARACTER_LOCATION_EX",
    "hex": "0xFF1B",
    "description": (
      "Like CHECK_CHARACTER_LOCATION but also fails if the matching entity is "
      "one of the 7 tracked party/vehicle entity slots "
      "(dword_C76640..dword_C76658).  Used to exclude party members from "
      "NPC location checks."
    ),
  },
  -228: {
    "opcode": "CHECK_CHARACTER_LOCATION_2",
    "hex": "0xFF1C",
    "description": (
      "Passes if secondary tracked entity (dword_C75D10) has location code "
      "(param1+param2*256)."
    ),
  },
  -227: {
    "opcode": "CHECK_CHARACTER_DISTANCE",
    "hex": "0xFF1D",
    "description": (
      "Passes if dword_C75D10 entity has location code (param1+param2*256) AND "
      "is not a party/vehicle slot AND the camera-space angle to that entity is "
      "<= 512 (roughly within ~11 degrees).  Excludes all 7 party-entity slots "
      "from matching."
    ),
  },
  -226: {
    "opcode": "FAIL",
    "hex": "0xFF1E",
    "description": (
      "Always fails (returns -1).  Can be used as a placeholder or to force "
      "the ELSE branch unconditionally."
    ),
  },
  -224: {
    "opcode": "CHECK_BUTTON_INPUT",
    "hex": "0xFF20",
    "description": (
      "Passes if a button/joystick input condition is met.  "
      "param1+param2*256 == -1 (0xFFFF): passes if ALL analogue axes are "
      "within ±45° dead-zone AND a digital edge is registered on the current "
      "frame.  Otherwise param is a button bitmask; passes if the AND of that "
      "mask against the current and previous frame input differs (edge detected).  "
      "Fails immediately if dword_2040A38 (battle/cutscene lock) is set."
    ),
  },
  -223: {
    "opcode": "CHECK_BATTLE_STATE",
    "hex": "0xFF21",
    "description": (
      "Passes if (dword_2040A34 != 0) OR "
      "((party_save[109] & 1) == (param1+param2*256)).  "
      "Used to check whether a battle has just been won/lost "
      "(battle-result byte at dword_20403A4+109)."
    ),
  },
  -222: {
    "opcode": "CHECK_LOCATION_DRAW_REGISTER",
    "hex": "0xFF22",
    "description": (
      "Passes if the current location-draw register index equals "
      "(param1+param2*256).  The index is computed as "
      "(Worldmap_weirdregister0_LocationDRAW - Worldmap_weirdregister_LocationDRAW - 4) >> 4, "
      "i.e. which location-block is currently rendered."
    ),
  },
  -219: {
    "opcode": "CHECK_WORLD_MAP_STATE",
    "hex": "0xFF25",
    "description": (
      "Passes if byte_2036B70 (world-map action state) == (param1+param2*256).  "
      "Known state values: 0=normal, 5=Ragnarok active, 6=Ragnarok approaching, "
      "7=Shumi vehicle, 8=Balamb Garden active, 9=Balamb Garden approaching, "
      "10=draw-point active, 13=exiting to field, 14=vehicle transition."
    ),
  },
  -217: {
    "opcode": "CHECK_BIT_FLAG",
    "hex": "0xFF27",
    "description": (
      "Passes if the save-game flag bit equals param2.  "
      "param1 = bit index 0-63 (0-31 → dword at dword_20403A4+116; "
      "32-63 → dword at dword_20403A4+120).  "
      "param2 = expected bit value (0 or 1)."
    ),
  },
  -215: {
    "opcode": "CHECK_DIALOG_STATE",
    "hex": "0xFF29",
    "description": (
      "Evaluates dialog slot param1+param2*256 and stores the result in "
      "dword_20402D8 for use by COMPARE_DIALOG_RESPONSE.  "
      "Passes if the slot is active (state >= 0), i.e. the dialog window "
      "has been opened via SHOW_TEXT_BOX or SHOW_CHOICE_BOX.  "
      "The stored value is the player's current choice index (0-based) or "
      "animation-progress counter."
    ),
  },
  -214: {
    "opcode": "COMPARE_DIALOG_RESPONSE",
    "hex": "0xFF2A",
    "description": (
      "Passes if dword_20402D8 (set by the preceding CHECK_DIALOG_STATE) "
      "equals (param1+param2*256).  Used to branch on which choice the "
      "player selected in a SHOW_CHOICE_BOX dialog."
    ),
  },
  -212: {
    "opcode": "CHECK_DIALOG_CONFIRMED",
    "hex": "0xFF2C",
    "description": (
      "Passes if sub_543AE0(param1) == param2.  "
      "sub_543AE0 returns TRUE when dialog slot param1 is active AND the "
      "player has pressed the confirm button (TEXT_LAYER[slot].unk_28 != 0).  "
      "param2 = expected boolean (0 or 1)."
    ),
  },
  -211: {
    "opcode": "COMPARE_SCRIPT_VAR",
    "hex": "0xFF2D",
    "description": (
      "Passes if script variable byte[param1] == param2.  "
      "Up to 2 variables (param1 = 0 or 1) at dword_20403A4+124.  "
      "These bytes are written by SET_SCRIPT_VAR (-210) and are persistent "
      "within the save-game party block."
    ),
  },
  -209: {
    "opcode": "CHECK_RANDOM_NUMBER",
    "hex": "0xFF2F",
    "description": (
      "Passes if a random uint16 (two successive calls to sub_541F10 packed "
      "as high/low byte) is < (param1+param2*256).  "
      "Effectively a probability gate: value 0=never, 65535=always."
    ),
  },
  -208: {
    "opcode": "COMPARE_SCRIPT_VAR_GT",
    "hex": "0xFF30",
    "description": (
      "Passes if param2 > script_variable_byte[param1] "
      "(dword_20403A4+124+param1)."
    ),
  },
  -207: {
    "opcode": "COMPARE_SCRIPT_VAR_LT",
    "hex": "0xFF31",
    "description": (
      "Passes if param2 < script_variable_byte[param1] "
      "(dword_20403A4+124+param1)."
    ),
  },
  -206: {
    "opcode": "CHECK_LOCATION_FLAG",
    "hex": "0xFF32",
    "description": (
      "Passes if (param1+param2*256) != ((~location_flags[14] & 8) != 0).  "
      "Checks bit 3 of the location-block flags byte "
      "(Worldmap_weirdregister0_LocationDRAW+14); inverted, so param=0 passes "
      "when the flag IS set."
    ),
  },
  -205: {
    "opcode": "COMPARE_LOCATION_BYTE",
    "hex": "0xFF33",
    "description": (
      "Passes if param1 == location_block_byte13 "
      "(Worldmap_weirdregister0_LocationDRAW+13).  "
      "Compares a per-location data byte, e.g. location/region sub-id."
    ),
  },
  -204: {
    "opcode": "CHECK_COMBAT_SCENE_ID",
    "hex": "0xFF34",
    "description": (
      "Passes if (param1+param2*256) == COMBAT_SCENE_ID.  "
      "Checks which battle scene was most recently loaded/fought."
    ),
  },
  -203: {
    "opcode": "CHECK_BATTLE_RESULT",
    "hex": "0xFF35",
    "description": (
      "Passes if battle_result_byte (byte_1CFF6E7) == 4.  "
      "No parameter is read; the condition is always the same fixed check."
    ),
  },
  -200: {
    "opcode": "CHECK_MOVEMENT",
    "hex": "0xFF38",
    "description": (
      "Passes if (isStateOfMovement != 0) == (param1+param2*256).  "
      "param=1 passes when the player is currently moving; param=0 passes "
      "when standing still."
    ),
  },
  -199: {
    "opcode": "CHECK_BATTLEVAR",
    "hex": "0xFF39",
    "description": (
      "Passes if (param1+param2*256) == SG_UNKNOWN_BATTLE_VAR.  "
      "Checks an unknown battle-related save-game variable."
    ),
  },

  # ── ACTION OPCODES  (used inside EXEC blocks, executed by sub_54D7E0) ───────

  -237: {
    "opcode": "ADD_ENTITY",
    "hex": "0xFF13",
    "description": (
      "Registers an entity in the active entity list (Section 9 only).  "
      "param1 = entity_type (e.g. 0=Squall, 1=Seifer, 3=Chocobo, 33=bike, "
      "48=Balamb Garden, 50=Ragnarok, 64-66=Galbadia vehicles, 80=SeeD ship, "
      "94=Lunatic Pandora …).  "
      "param2 = entity_id slot override, or 0xFF for default.  "
      "The entity will be spawned on the world map when this EXEC block fires."
    ),
  },
  -236: {
    "opcode": "ADD_ENTITY_ALT",
    "hex": "0xFF14",
    "description": (
      "Alternate form of ADD_ENTITY with the same parameter layout "
      "(param1=entity_type, param2=entity_id/0xFF).  "
      "Handled identically to ADD_ENTITY by sub_544860."
    ),
  },
  -225: {
    "opcode": "SHOW_TEXT_BOX",
    "hex": "0xFF1F",
    "description": (
      "Opens a text dialog window (no choices) in slot param1.  "
      "param1 = dialog slot index (0-15, indexes into byte_C761A0[16*slot]).  "
      "param2 = string id from wmsetS14 (Section 14 dialog text table).  "
      "Lays out the window at a pre-configured screen position for the slot.  "
      "Use CLOSE_TEXT_BOX to dismiss it."
    ),
  },
  -221: {
    "opcode": "SHOW_CHOICE_BOX",
    "hex": "0xFF23",
    "description": (
      "Opens a multiple-choice dialog window in slot param1.  "
      "param1 = dialog slot index.  param2 = string id from wmsetS14.  "
      "Additional choice option ids are hard-coded per call-site (args 3-7 in "
      "sub_5438D0: first_choice, last_choice, cancel_choice, default_choice).  "
      "Player's selection is later read with CHECK_DIALOG_STATE + "
      "COMPARE_DIALOG_RESPONSE."
    ),
  },
  -220: {
    "opcode": "CLOSE_TEXT_BOX",
    "hex": "0xFF24",
    "description": (
      "Closes / hides the dialog window in slot (param1+param2*256).  "
      "Sets slot state to -1 (inactive) and calls sub_4A0660 to dismiss the "
      "text layer."
    ),
  },
  -218: {
    "opcode": "SET_WORLD_MAP_STATE",
    "hex": "0xFF26",
    "description": (
      "Sets byte_2036B70 (world-map action state) = param1.  "
      "Controls what actions / transitions are currently active.  "
      "See CHECK_WORLD_MAP_STATE for known values."
    ),
  },
  -216: {
    "opcode": "SET_BIT_FLAG",
    "hex": "0xFF28",
    "description": (
      "Sets or clears a save-game flag bit.  "
      "param1 = bit index 0-63 (0-31 → dword_20403A4+116; "
      "32-63 → dword_20403A4+120).  "
      "param2 = new bit value: 1 = set, 0 = clear."
    ),
  },
  -210: {
    "opcode": "SET_SCRIPT_VAR",
    "hex": "0xFF2E",
    "description": (
      "Sets script variable byte[param1] = param2.  "
      "param1 = index 0 or 1 (bytes at dword_20403A4+124 / +125).  "
      "These bytes are readable by COMPARE_SCRIPT_VAR / _GT / _LT."
    ),
  },
  -202: {
    "opcode": "SET_GLOBAL_EVENT_TRIGGERED",
    "hex": "0xFF36",
    "description": (
      "Sets dword_2040A40 = 1 with no parameters (param1 and param2 are "
      "ignored, instruction advances 4 bytes).  Marks that a global world-map "
      "event has been triggered; suppresses further trigger checks this frame."
    ),
  },
  -201: {
    "opcode": "ADD_ITEM",
    "hex": "0xFF37",
    "description": (
      "Adds an item to the party inventory.  "
      "param1 = item id (0-255).  "
      "param2 = quantity (1-255).  "
      "Calls AddItemToInventory(param1, param2) at 0x47ED00."
    ),
  },
}
