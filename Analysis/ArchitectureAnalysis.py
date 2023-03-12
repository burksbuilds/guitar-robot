# -*- coding: utf-8 -*-
"""
Created on Fri Mar 10 16:38:35 2023

@author: andrew
"""

import json
import itertools


finger_names = ['None', 'Index', 'Middle', 'Ring', 'Pinky', 'Barre']
primary_fingers = [1,2]
secondary_fingers = [3,4]

class AnalysisConfig(object):
    def __init__(self):
        self.min_accessible_string = [1,1,1,1,1,1] #indexed by finger actuator
        self.max_accessible_string = [6,6,6,6,6,6] #indexed by finger actuator
        self.min_adjacent_strings =  [6,1,1,1,1,1] #indexed by finger actuator
        self.max_adjacent_strings =  [6,1,1,1,1,6] #indexed by finger actuator
        self.max_accessible_fret = [0,20,20,20,20,0]
        self.body_fret_offset = [0,0,0,0,0,0] #the body of the finger is offset this many frets, blocking notes on adjacent frets
        self.allow_barre_crossing = False
        self.force_primary_low = 0
        self.force_primary_spacing = 0
    
class BarreConfig(AnalysisConfig):
    
    def __init__(self):
        super().__init__()
        self.min_adjacent_strings =  [6,1,1,1,1,4] #indexed by finger actuator
        self.max_adjacent_strings =  [6,2,2,1,1,6] #indexed by finger actuator
        self.max_accessible_fret = [0,16,16,20,20,16]
        
class OverlapConfig(AnalysisConfig):
    
    def __init__(self):
        super().__init__()
        self.min_adjacent_strings =  [6,1,1,1,1,6] #indexed by finger actuator
        self.max_adjacent_strings =  [6,2,2,1,1,6] #indexed by finger actuator
        self.max_accessible_fret = [0,16,16,20,20,16]
        self.body_fret_offset = [0,0,1,0,1,0] #the body of the finger is offset this many frets, blocking notes on adjacent frets

class ReachConfig(AnalysisConfig):
    def __init__(self):
        super().__init__()
        self.min_adjacent_strings =  [6,1,1,1,1,6] #indexed by finger actuator
        self.max_adjacent_strings =  [6,2,2,1,1,6] #indexed by finger actuator
        self.max_accessible_fret = [0,16,16,20,20,16]
        self.body_fret_offset = [0,0,1,0,1,0] #the body of the finger is offset this many frets, blocking notes on adjacent frets
        self.force_primary_low = 1
        self.force_primary_spacing = 1

# start string must be less than end string 
#returns true if fretting all strings between start and end at fret will not interfere with other frets           
def can_barre(fret, start_string, end_string, string_map):
    #print(f"      Checking for bar on {fret} [{start_string},{end_string}]")
    if end_string >= start_string: return False
    for string in range(start_string,end_string+1):
        if string in string_map and string_map[string] < fret: return False
    return True

def get_barre_zone(fret, string, string_map):
    upper_string = string
    while upper_string < 6 and (not((upper_string+1) in string_map) or string_map[upper_string+1] >= fret):
        upper_string += 1
    lower_string = string
    while lower_string > 1 and (not((lower_string-1) in string_map) or string_map[lower_string-1] >= fret):
        lower_string -= 1
    return (upper_string, lower_string)

def yield_barres_of_fret(fret, string_map, fret_map):
    for barre_zone in list(set([get_barre_zone(fret, string, string_map) for string in fret_map[fret]])):
        #print(f"BARRE ZONE f{fret} {barre_zone}")
        if barre_zone[0] == barre_zone[1]:
            continue
        for end_finger in range(barre_zone[1],barre_zone[0]):
            for start_finger in range(end_finger+1,barre_zone[0]+1):
                #print(f"  SUB ZONE f{fret} {(start_finger, end_finger)}")
                yield (start_finger,end_finger)

            
def yield_fret_groupings_of_fret(fret, string_map, fret_map):
    yield [(fret,string,string) for string in fret_map[fret]] #default case - no barres
    for barre_start,barre_end in yield_barres_of_fret(fret, string_map, fret_map):
        yield [(fret,string,string) for string in fret_map[fret] if (string > barre_start or string < barre_end)] + [(fret, barre_start, barre_end)]
        
def yield_fret_grouping_cases_recursive(i_fret, string_map, fret_map):
    
    if i_fret >= len(fret_map.keys()):
        yield []
        return
    if list(fret_map.keys())[i_fret] == 0:
        i_fret = i_fret + 1
    if i_fret >= len(fret_map.keys()):
        yield []
        return
    
    #print(f"  Evaluating Fret Groupings on i{i_fret} (#{list(fret_map.keys())[i_fret]})")
    this_fret_groupings = list(yield_fret_groupings_of_fret(list(fret_map.keys())[i_fret], string_map, fret_map))
    #print(f"    This Fret Groupings{this_fret_groupings}")
    partial_fret_groupings = list(yield_fret_grouping_cases_recursive(i_fret+1, string_map, fret_map))
    for this_fret_grouping in this_fret_groupings:
        for partial_fret_grouping in partial_fret_groupings:
            #print(f"    YIELD @{i_fret} {this_fret_grouping} AND {partial_fret_grouping}")
            yield this_fret_grouping + partial_fret_grouping
        
# returns all potential fingers of the supplied fret groupings (fret, stringstart, stringend) by putting them in a dict with finger as key
def yield_fret_grouping_fingerings_recursive(fret_groupings, fingers):
    num_fret_groupings = len(fret_groupings)
    if num_fret_groupings > len(fingers)-1:
        return
    
    for finger_orders in itertools.permutations(fingers, num_fret_groupings):
        yield {fingers[finger_orders[i]]:fret_groupings[i] for i in range(num_fret_groupings)}

def is_valid_base_fingering(fingering, positions):
    if 1 in fingering and 2 in fingering and fingering[1][0] > fingering[2][0]:
        #print(f"  ! Failed because index finger (#1) is at a higher fret {fingering[1][0]} than the middle finger (#2) {fingering[2][0]}")
        return False
    if 3 in fingering and 4 in fingering and fingering[3][0] > fingering[4][0]:
        #print(f"  ! Failed because ring finger (#3) is at a higher fret {fingering[3][0]} than the pinky finger (#4) {fingering[4][0]}")
        return False
    if 5 in fingering:
        for finger in fingering:
            if finger != 5 and fingering[finger][0] == fingering[5][0]:
                #print(f"  ! Failed because barre finger (#5) is at the same fret {fingering[5][0]} as the {finger_names[finger]} finger (#{finger}) {fingering[finger][0]}")
                return False
    return True
    
def is_valid_fingering(fingering, positions, config):
    #print(f"  Evaluating Fingering for Position {positions}: {fingering}")

    for secondary_finger in secondary_fingers:
        if secondary_finger in fingering:
            blocked_fret = fingering[secondary_finger][0]+config.body_fret_offset[secondary_finger]
            for finger in fingering:
                if finger != secondary_finger and fingering[finger][0] == blocked_fret and fingering[finger][2] < fingering[secondary_finger][1]:
                    return False
    if 1 in fingering and 2 in fingering and fingering[1][0] == fingering[2][0]:
        if config.body_fret_offset[1] == config.body_fret_offset[2]:
            return False
        spacing = 6
        if fingering[1][2] > fingering[2][1]: #index finger is on a lower string
            if config.force_primary_low == 2:
                return False
            spacing = fingering[1][2] - fingering[2][1] - 1
        elif fingering[1][1] < fingering[2][2]: #index finger is on a higher string
            if config.force_primary_low == 1:
                return False
            spacing = fingering[2][2] - fingering[1][1] - 1
        else: #the fingers overlap! probably should have caught this sooner...
            return False
        if spacing < config.force_primary_spacing:
            return False
    
    for finger in fingering:
        if fingering[finger][0] > config.max_accessible_fret[finger]:
            return False
        if fingering[finger][1] > config.max_accessible_string[finger]:
            return False
        if fingering[finger][2] < config.min_accessible_string[finger]:
            return False
        if (fingering[finger][1] - fingering[finger][2]+1) > config.max_adjacent_strings[finger]:
            return False
        if (fingering[finger][1] - fingering[finger][2]+1) < config.min_adjacent_strings[finger]:
            return False
        
    
    
    return True
    
        

# generator that returns every possible fingering for the given position given the finger actuator constraints
def yield_fingerings(positions):
    #print(f"Position: {positions}")
    string_map = {6-i:int(p) for i,p in enumerate(positions) if p.isnumeric()} #keys are only those strings being played (#6 -> #1), val is fret of string
    distinct_frets = list(set((int(p) for p in positions if p.isnumeric())))
    fret_map = {fret: [6-i for i, p in enumerate(positions) if p == str(fret)] for fret in distinct_frets} #keys are only those frets being used (#0->?), val are strings held at fret
    
    all_potential_fret_groupings = list(yield_fret_grouping_cases_recursive(0, string_map, fret_map))
    for fret_groupings in all_potential_fret_groupings:
        #print(f"  Potential Fret Grouping: {fret_groupings}")
        for fingering in yield_fret_grouping_fingerings_recursive(fret_groupings,range(0,len(finger_names))):
            if is_valid_base_fingering(fingering, positions):
                yield fingering
    

chords_file = open("chords.json")
chords_json = json.load(chords_file)
chords_file.close()


barre_configs = dict()

barre_configs['barre4_pointer2'] = BarreConfig()

barre_configs['barre4_pointer2_pinkyL'] = BarreConfig()
barre_configs['barre4_pointer2_pinkyL'].body_fret_offset[4] = 1

barre_configs['barre4_pointer2_middleL'] = BarreConfig()
barre_configs['barre4_pointer2_middleL'].body_fret_offset[2] = 1

barre_configs['barre4_pointer2_middleL_pinkyL'] = BarreConfig()
barre_configs['barre4_pointer2_middleL_pinkyL'].body_fret_offset[4] = 1
barre_configs['barre4_pointer2_middleL_pinkyL'].body_fret_offset[2] = 1

barre_configs['barre5_pointer2_middleL_pinkyL'] = BarreConfig()
barre_configs['barre5_pointer2_middleL_pinkyL'].body_fret_offset[4] = 1
barre_configs['barre5_pointer2_middleL_pinkyL'].body_fret_offset[2] = 1
barre_configs['barre5_pointer2_middleL_pinkyL'].min_adjacent_strings[5] = 5

barre_configs['barre6_pointer2_middleL_pinkyL'] = BarreConfig()
barre_configs['barre6_pointer2_middleL_pinkyL'].body_fret_offset[4] = 1
barre_configs['barre6_pointer2_middleL_pinkyL'].body_fret_offset[2] = 1
barre_configs['barre6_pointer2_middleL_pinkyL'].min_adjacent_strings[5] = 6

barre_configs['barreX_pointer2'] = BarreConfig()
barre_configs['barreX_pointer2'].max_accessible_fret[5] = 0

barre_configs['barreX_pointer6'] = BarreConfig()
barre_configs['barreX_pointer6'].max_accessible_fret[5] = 0
barre_configs['barreX_pointer6'].max_adjacent_strings[1] = 6

barre_configs['barreX_pointer6_middle4'] = BarreConfig()
barre_configs['barreX_pointer6_middle4'].max_accessible_fret[5] = 0
barre_configs['barreX_pointer6_middle4'].max_adjacent_strings[1] = 6
barre_configs['barreX_pointer6_middle4'].max_adjacent_strings[2] = 4


barre_configs['barreX_pointer6_pinkyL'] = BarreConfig()
barre_configs['barreX_pointer6_pinkyL'].max_accessible_fret[5] = 0
barre_configs['barreX_pointer6_pinkyL'].max_adjacent_strings[1] = 6
barre_configs['barreX_pointer6_pinkyL'].body_fret_offset[4] = 1

barre_configs['barreX_pointer6_middle4_pinkyL'] = BarreConfig()
barre_configs['barreX_pointer6_middle4_pinkyL'].max_accessible_fret[5] = 0
barre_configs['barreX_pointer6_middle4_pinkyL'].max_adjacent_strings[1] = 6
barre_configs['barreX_pointer6_middle4_pinkyL'].body_fret_offset[4] = 1
barre_configs['barreX_pointer6_middle4_pinkyL'].max_adjacent_strings[2] = 4

barre_configs['barreX_pointer6_middleL_pinkyL'] = BarreConfig()
barre_configs['barreX_pointer6_middleL_pinkyL'].max_accessible_fret[5] = 0
barre_configs['barreX_pointer6_middleL_pinkyL'].max_adjacent_strings[1] = 6
barre_configs['barreX_pointer6_middleL_pinkyL'].body_fret_offset[4] = 1
barre_configs['barreX_pointer6_middleL_pinkyL'].body_fret_offset[2] = 1

barre_configs['barreX_pointer6_middle4L_pinkyL'] = BarreConfig()
barre_configs['barreX_pointer6_middle4L_pinkyL'].max_accessible_fret[5] = 0
barre_configs['barreX_pointer6_middle4L_pinkyL'].max_adjacent_strings[1] = 6
barre_configs['barreX_pointer6_middle4L_pinkyL'].body_fret_offset[4] = 1
barre_configs['barreX_pointer6_middle4L_pinkyL'].body_fret_offset[2] = 1
barre_configs['barreX_pointer6_middle4L_pinkyL'].max_adjacent_strings[2] = 4




overlap_configs = dict()

overlap_configs['gap0'] = OverlapConfig()

overlap_configs['gap0_pointerLow'] = OverlapConfig()
overlap_configs['gap0_pointerLow'].force_primary_low = 1

overlap_configs['gap0_middleLow'] = OverlapConfig()
overlap_configs['gap0_middleLow'].force_primary_low = 2

overlap_configs['gap1'] = OverlapConfig()
overlap_configs['gap1'].force_primary_spacing = 1

overlap_configs['gap1_pointerLow'] = OverlapConfig()
overlap_configs['gap1_pointerLow'].force_primary_spacing = 1
overlap_configs['gap1_pointerLow'].force_primary_low = 1

overlap_configs['gap1_middleLow'] = OverlapConfig()
overlap_configs['gap1_middleLow'].force_primary_spacing = 1
overlap_configs['gap1_middleLow'].force_primary_low = 2

overlap_configs['gap2'] = OverlapConfig()
overlap_configs['gap2'].force_primary_spacing = 2

overlap_configs['gap2_pointerLow'] = OverlapConfig()
overlap_configs['gap2_pointerLow'].force_primary_spacing = 2
overlap_configs['gap2_pointerLow'].force_primary_low = 1

overlap_configs['gap2_middleLow'] = OverlapConfig()
overlap_configs['gap2_middleLow'].force_primary_spacing = 2
overlap_configs['gap2_middleLow'].force_primary_low = 2




reach_configs = dict()

reach_configs['f6_m6_r6_p6'] = ReachConfig()


reach_configs['f6_m5_r6_p6'] = ReachConfig()
reach_configs['f6_m5_r6_p6'].max_accessible_string[2] = 5

reach_configs['f6_m6_r5_p6'] = ReachConfig()
reach_configs['f6_m6_r5_p6'].max_accessible_string[3] = 5


reach_configs['f6_m4_r6_p6'] = ReachConfig()
reach_configs['f6_m4_r6_p6'].max_accessible_string[2] = 4

reach_configs['f6_m6_r4_p6'] = ReachConfig()
reach_configs['f6_m6_r4_p6'].max_accessible_string[3] = 4


reach_configs['f6_m5_r5_p6'] = ReachConfig()
reach_configs['f6_m5_r5_p6'].max_accessible_string[2] = 5
reach_configs['f6_m5_r5_p6'].max_accessible_string[3] = 5


reach_configs['f6_m4_r5_p6'] = ReachConfig()
reach_configs['f6_m4_r5_p6'].max_accessible_string[2] = 4
reach_configs['f6_m4_r5_p6'].max_accessible_string[3] = 5

reach_configs['f6_m5_r4_p6'] = ReachConfig()
reach_configs['f6_m5_r4_p6'].max_accessible_string[2] = 5
reach_configs['f6_m5_r4_p6'].max_accessible_string[3] = 4

reach_configs['f6_m4_r4_p6'] = ReachConfig()
reach_configs['f6_m4_r4_p6'].max_accessible_string[2] = 4
reach_configs['f6_m4_r4_p6'].max_accessible_string[3] = 4

reach_configs['f6_m4_r3_p6'] = ReachConfig()
reach_configs['f6_m4_r3_p6'].max_accessible_string[2] = 4
reach_configs['f6_m4_r3_p6'].max_accessible_string[3] = 3

reach_configs['f6_m3_r4_p6'] = ReachConfig()
reach_configs['f6_m3_r4_p6'].max_accessible_string[2] = 3
reach_configs['f6_m3_r4_p6'].max_accessible_string[3] = 4

reach_configs['f2_m5_r4_p6'] = ReachConfig()
reach_configs['f2_m5_r4_p6'].max_accessible_string[2] = 5
reach_configs['f2_m5_r4_p6'].max_accessible_string[3] = 4
reach_configs['f2_m5_r4_p6'].min_accessible_string[1] = 2

reach_configs['f2_m4_r4_p6'] = ReachConfig()
reach_configs['f2_m4_r4_p6'].max_accessible_string[2] = 4
reach_configs['f2_m4_r4_p6'].max_accessible_string[3] = 4
reach_configs['f2_m4_r4_p6'].min_accessible_string[1] = 2

reach_configs['f3_m4_r4_p6'] = ReachConfig()
reach_configs['f3_m4_r4_p6'].max_accessible_string[2] = 4
reach_configs['f3_m4_r4_p6'].max_accessible_string[3] = 4
reach_configs['f3_m4_r4_p6'].min_accessible_string[1] = 3

reach_configs['f2_m3_r4_p6'] = ReachConfig()
reach_configs['f2_m3_r4_p6'].max_accessible_string[2] = 3
reach_configs['f2_m3_r4_p6'].max_accessible_string[3] = 4
reach_configs['f2_m3_r4_p6'].min_accessible_string[1] = 2

reach_configs['f3_m3_r4_p6'] = ReachConfig()
reach_configs['f3_m3_r4_p6'].max_accessible_string[2] = 3
reach_configs['f3_m3_r4_p6'].max_accessible_string[3] = 4
reach_configs['f3_m3_r4_p6'].min_accessible_string[1] = 3




barre_file = open("barre_analysis.csv", 'w')
barre_file.write("Configuration;Chord;Position;Fingerings\n")

overlap_file = open("overlap_analysis.csv", 'w')
overlap_file.write("Configuration;Chord;Position;Fingerings\n")

reach_file = open("reach_analysis.csv", 'w')
reach_file.write("Configuration;Chord;Position;Fingerings\n")

num_positions = 0
for chord in chords_json:
    num_positions += len(chords_json[chord])


i_position = 0
for chord in chords_json:
    for chord_position in chords_json[chord]:
        position_fingerings = list(yield_fingerings(chord_position['positions']))
        i_position += 1
        for config in barre_configs:
            valid_fingering_count = 0
            for fingering in position_fingerings:
                if is_valid_fingering(fingering, chord_position['positions'], barre_configs[config]):
                    valid_fingering_count += 1
            barre_file.write(f"{config};{chord};{chord_position['positions']};{valid_fingering_count}\n")
            print(f"{100*i_position/num_positions:6.1f}%\t{valid_fingering_count}\t{config}\t\t{chord}\t\t{chord_position['positions']}")
        for config in overlap_configs:
            valid_fingering_count = 0
            for fingering in position_fingerings:
                if is_valid_fingering(fingering, chord_position['positions'], overlap_configs[config]):
                    valid_fingering_count += 1
            overlap_file.write(f"{config};{chord};{chord_position['positions']};{valid_fingering_count}\n")
            print(f"{100*i_position/num_positions:6.1f}%\t{valid_fingering_count}\t{config}\t\t{chord}\t\t{chord_position['positions']}")
        for config in reach_configs:
            valid_fingering_count = 0
            for fingering in position_fingerings:
                if is_valid_fingering(fingering, chord_position['positions'], reach_configs[config]):
                    valid_fingering_count += 1
            reach_file.write(f"{config};{chord};{chord_position['positions']};{valid_fingering_count}\n")
            print(f"{100*i_position/num_positions:6.1f}%\t{valid_fingering_count}\t{config}\t\t{chord}\t\t{chord_position['positions']}")

    
barre_file.close()
overlap_file.close()
reach_file.close()