# -*- coding: utf-8 -*-
"""
Created on Mon Mar 13 09:30:03 2023

@author: andre
"""

import json
import itertools
import guitarpro as gp
import networkx as nx
import math

finger_names = ['None', 'Index', 'Middle', 'Ring', 'Pinky', 'Barre']
primary_fingers = [1,2]
secondary_fingers = [3,4]
max_adjacent_strings =  [6,2,2,1,1,6]
min_adjacent_strings =  [1,1,1,1,1,6]
finger_restrictions = {1:(2,-1), 2:(1,1),3:(4,-1),4:(3,1)}
complementary_finger_map = {1:2,2:1,3:4,4:3}

class AnalysisConfig(object):
    def __init__(self):
        self.min_accessible_string = [1,2,1,1,1,1] #indexed by finger actuator
        self.max_accessible_string = [6,6,3,4,6,6] #indexed by finger actuator
        self.max_accessible_fret = [0,16,16,20,20,16]
        self.body_fret_offset = [0,0,1,0,1,0] #the body of the finger is offset this many frets, blocking notes on adjacent frets
        self.allow_barre_crossing = False
        self.allow_single_string_barre = True
        self.force_primary_low = 1
        self.force_primary_spacing = 1
        
        


def yield_barres_of_fret(fret, string_map, fret_map):
    #check for full barre on highest fret
    blocked_strings = [string for string in string_map if string_map[string] < fret]
    if not blocked_strings:
        yield (6,1)
    #check for 2-barres on any fret
    strings = fret_map[fret]
    for i_string in range(0,len(strings)-1):
        if strings[i_string] - strings[i_string+1] == 1:
            yield (strings[i_string], strings[i_string+1])
    #check for possible masked 2-barres. not because they are a better option than just oen finger...but when comign from another note it could be handy
    for string in fret_map[fret]:
        if not((string+1) in string_map and string_map[string+1] <= fret):
            yield ((string+1),string)
        if not((string-1) in string_map and string_map[string-1] <= fret):
            yield (string,(string-1))
            
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
        
# returns all potential fingerings of the supplied fret groupings (fret, stringstart, stringend) by putting them in a dict with finger as key
def yield_fret_grouping_fingerings_recursive(fret_groupings, fingers):
    num_fret_groupings = len(fret_groupings)
    if num_fret_groupings > len(fingers)-1:
        return
    
    for finger_orders in itertools.permutations(fingers, num_fret_groupings):
        yield {finger_orders[i]:fret_groupings[i] for i in range(num_fret_groupings)}

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
    for finger in fingering:
        if fingering[finger][1] > 0:
            if (fingering[finger][1] - fingering[finger][2]+1) > max_adjacent_strings[finger]:
                return False
            if (fingering[finger][1] - fingering[finger][2]+1) < min_adjacent_strings[finger]:
                return False
    return True
    
def is_valid_fingering(fingering, positions, config):
    #print(f"  Evaluating Fingering for Position {positions}: {fingering}")

    for secondary_finger in secondary_fingers:
        if secondary_finger in fingering and fingering[secondary_finger][1] > 0:
            blocked_fret = fingering[secondary_finger][0]+config.body_fret_offset[secondary_finger]
            for finger in fingering:
                if finger != secondary_finger and fingering[finger][1] > 0 and fingering[finger][0] == blocked_fret and fingering[finger][2] < fingering[secondary_finger][1]:
                    return False
    if 1 in fingering and 2 in fingering and fingering[1][1] > 0 and fingering[2][1] > 0 and fingering[1][0] == fingering[2][0]:
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
        if fingering[finger][1] > 0:
            if fingering[finger][0] > config.max_accessible_fret[finger]:
                return False
            if fingering[finger][1] > config.max_accessible_string[finger]:
                return False
            if fingering[finger][2] < config.min_accessible_string[finger]:
                return False
            
    if not config.allow_barre_crossing:
        for finger in fingering:
            if finger != 5 and fingering[finger][0] < fingering[5][0]:
                return False
    if not config.allow_single_string_barre and 5 in fingering and fingering[5][1] > 0:
        held_strings = sum(1 for p in positions if p.isnumeric() and int(p) == fingering[5][0])
        if held_strings <= 1:
            return False

    return True


# generator that returns every possible fingering for the given position given the finger actuator constraints
def yield_partial_fingerings(positions,fingers):
    #print(f"Position: {positions}")
    string_map = {6-i:int(p) for i,p in enumerate(positions) if p.isnumeric()} #keys are only those strings being played (#6 -> #1), val is fret of string
    distinct_frets = list(set((int(p) for p in positions if p.isnumeric())))
    fret_map = {fret: [6-i for i, p in enumerate(positions) if p == str(fret)] for fret in distinct_frets} #keys are only those frets being used (#0->?), val are strings held at fret
    
    all_potential_fret_groupings = list(yield_fret_grouping_cases_recursive(0, string_map, fret_map))
    for fret_groupings in all_potential_fret_groupings:
        #print(f"  Potential Fret Grouping: {fret_groupings}")
        for fingering in yield_fret_grouping_fingerings_recursive(fret_groupings,fingers):
            #print(f"    Potential Fingering: {fingering}")
            if is_valid_base_fingering(fingering, positions):
                yield fingering

def yield_potential_inactive_frets(finger, new_partial_fingering, old_fingerings):
    old_frets_of_finger = list(set(old_fingering[finger][0] for old_fingering in old_fingerings))
    for fret in old_frets_of_finger:
        yield fret
    if finger in complementary_finger_map and complementary_finger_map[finger] in new_partial_fingering and new_partial_fingering[complementary_finger_map[finger]][1] > 0:
        complementary_finger_fret = new_partial_fingering[complementary_finger_map[finger]][0]
        yield complementary_finger_fret
    if finger == 5:
        other_frets = [new_partial_fingering[f][0] for f in new_partial_fingering if new_partial_fingering[f][0] > 0]
        if other_frets and min(other_frets) < max(old_frets_of_finger):
            yield min(other_frets)-1
                
def yield_all_fingerings(finger,new_partial_fingering, old_fingerings):
    if finger in new_partial_fingering:
        yield new_partial_fingering[finger]
    else:
        potential_inactive_frets = list(set(f for f in yield_potential_inactive_frets(finger,new_partial_fingering, old_fingerings)))
        for fret in potential_inactive_frets:
            yield (fret,0,0)
       
    
def yield_all_fingerings_recursive(i_finger, fingers, new_partial_fingering, old_fingerings):
    for fingering in yield_all_fingerings(fingers[i_finger], new_partial_fingering, old_fingerings):
        if i_finger == 0:
            yield {fingers[i_finger]: fingering}
        else:
            for sub_fingering in yield_all_fingerings_recursive(i_finger-1, fingers, new_partial_fingering, old_fingerings):
               sub_fingering_copy = sub_fingering.copy()
               sub_fingering_copy[fingers[i_finger]] = fingering
               yield sub_fingering_copy

def yield_full_fingerings(positions, old_fingerings, config):
    fingers = list(range(1,len(finger_names)))
    for partial_fingering in yield_partial_fingerings(positions, fingers):
        for full_fingering in yield_all_fingerings_recursive(len(fingers)-1,fingers,partial_fingering,old_fingerings):
            #print(f"Potential fingering: {full_fingering}")
            if is_valid_base_fingering(full_fingering,positions) and is_valid_fingering(full_fingering,positions,config):
                yield full_fingering
    



class FingeringNode(object):
    def __init__(self,time,fingering,positions):
        self.fingering = fingering
        self.positions = positions
        self.time = time #not duration. this is when the fingering happens
    def __eq__(self, o):
        if o is None:
            return False
        return o.fingering == self.fingering and o.time == self.time

    def __hash__(self):
        return hash(self.__str__())
    
    def __str__(self):
        return f"t={self.time}: {self.fingering}"
    
def get_fret_position(fret_number, fret_scale_length = 25.5):
    return fret_scale_length - (fret_scale_length / math.pow(2 , (fret_number/12)))

def get_fret_transition_distance(start_fret, end_fret, fret_scale_length = 25.5):
    return abs(get_fret_position(start_fret,fret_scale_length) - get_fret_position(end_fret,fret_scale_length))

def get_finger_transition_time(finger, start_node, end_node):
    if start_node.fingering[finger][1] > 0:
        return abs(end_node.time - start_node.time)*0.2
    return abs(end_node.time - start_node.time)


def get_fret_range(finger, fingering):
    if fingering[finger][0] > 0:
        return (fingering[finger][0],fingering[finger][0])
    if finger in finger_restrictions:
        if fingering[finger_restrictions[finger][0]][0] == 0: #comparison finger is also unconstrained
            return (0,20)
        if finger_restrictions[finger][1] > 0: #this finger must be on a higher fret than the comparison finger
            return (fingering[finger_restrictions[finger][0]][0], 20)
        if finger_restrictions[finger][1] < 0: #this finger must be on a lower fret than the comparison finger
            return (0,fingering[finger_restrictions[finger][0]][0])
    return (0,20)

def get_smallest_possible_distance(finger,start_fingering, end_fingering, fret_scale_length = 25.5):
    start_range = get_fret_range(finger,start_fingering) #all possible frets finger could start on
    end_range = get_fret_range(finger,end_fingering) #all possible frets finger could end on
    if start_range[1] < end_range[0]:#all fo start range less than all of end range
        return get_fret_transition_distance(start_range[1], end_range[0], fret_scale_length)
    elif end_range[1] < start_range[0]:#all of end range less than all of start range
        return get_fret_transition_distance(start_range[0], end_range[1], fret_scale_length)
    return 0
    

def get_finger_transition_cost(finger, start_node, end_node, fret_scale_length = 25.5):
    distance = get_smallest_possible_distance(finger, start_node.fingering, end_node.fingering, fret_scale_length)
    time = get_finger_transition_time(finger, start_node, end_node)
    if time <= 0: 
        return float('inf')
    cost = distance / (time * time)
    #print(f"  {finger} cost: {cost}")
    return cost
    
    
def get_finger_transition_costs_in_path(path, finger):
    nodes_where_fretting = [i for i,n in enumerate(path) if path.fingering[finger][0]>0]
    for i in range(len(nodes_where_fretting)-1):
        time = path[nodes_where_fretting[i+1]].time-path[nodes_where_fretting[i]+1].time
        if time <= 0:
            time = 0.2 * (path[nodes_where_fretting[i]].time - path[nodes_where_fretting[i]+1].time) #for back to back notes, assume 20% transition???
            
        yield get_finger_transition_cost(path[nodes_where_fretting[i]].fingering[finger], 
                                         path[nodes_where_fretting[i+1]].fingering[finger], 
                                         time)
    
    
def get_fingering_cost(fingering, positions):
    cost = 0
    for finger in fingering: #prefer not using barre
        if fingering[finger][1] > 0:
            held_strings = fingering[finger][1] - fingering[finger][2] + 1
            held_strings_played = sum(1 for p in positions if p.isnumeric() and int(p) == fingering[finger][0])
            cost += 1000*(held_strings - held_strings_played)
    #print(f"  Fingering cost: {cost}")
    return cost
    
    
def get_node_transition_cost(start_node, end_node, edge_attributes):
    #do i just use the max? or average? or sum? or product?
    return get_fingering_cost(end_node.fingering, end_node.positions) + max(get_finger_transition_cost(finger, start_node, end_node) for finger in start_node.fingering.keys())

def can_transition(start_node, end_node):
    #for finger in end_node.fingering:
    #    if end_node.fingering[finger][1] == 0 and (start_node.fingering[finger][0] != end_node.fingering[finger][0]):
    #        return False
    return True
        

idle_positions = ['x','x','x','x','x','x']
idle_fingering = {finger:(finger,0,0) for finger in range(1,len(finger_names))}
idle_fingering[5] = (0,0,0)
        
beat_duration = 1 / (180*4/60) #BPM * size_of_beat / to_seconds  <-invert

beats = [ 
#    ['x','9','x','x','x','x'],
#    ['x','x','7','x','x','x'],
#    ['x','x','x','6','x','x'],
#    ['x','x','x','x','7','x'],
#    ['x','x','x','x','x','5'],
#    ['x','x','x','x','x','9'],
#    ['x','x','x','x','x','17'],
#    ['x','x','x','x','x','9'],
#    ['x','x','x','x','x','5'],
#    ['x','x','x','x','7','x'],
#    ['x','x','x','6','x','x'],
#    ['x','x','7','x','x','x'],
#    ['x','10','x','x','x','x'],
#    ['x','x','9','x','x','x'],
#    ['x','x','x','7','x','x'],
#    ['x','x','x','x','8','x'],
#    ['x','x','x','x','x','7'],
#    ['x','x','x','x','x','10'],
#    ['x','x','x','x','x','15'],
#    ['x','x','x','x','x','10'],
#    ['x','x','x','x','x','7'],
#    ['x','x','x','x','8','x'],
#    ['x','x','x','7','x','x'], 
    
    ['x','x','9','x','x','x']]


config = AnalysisConfig()


graph = nx.DiGraph()

start_node = FingeringNode(-1*beat_duration,idle_fingering,idle_positions)
graph.add_node(start_node)

previous_nodes = [start_node]
possible_paths = 1

for i,beat_positions in enumerate(beats):
    previous_fingerings = list(node.fingering for node in previous_nodes)
    current_nodes = [FingeringNode(i*beat_duration,fingering,beat_positions) for fingering in yield_full_fingerings(beat_positions, previous_fingerings, config)]
    possible_paths *= len(current_nodes)
    for current_node in current_nodes:
        graph.add_node(current_node)
        #print(current_node)
        for previous_node in previous_nodes:
            if can_transition(previous_node,current_node):
                cost = get_node_transition_cost(previous_node, current_node, None) #if previous_node is not start_node else 0
                #print(cost)
                graph.add_edge(previous_node, current_node, weight=cost)
    previous_nodes = current_nodes
    
end_node = FingeringNode(len(beats)*beat_duration,idle_fingering,idle_positions)
for previous_node in previous_nodes:
    cost = get_node_transition_cost(previous_node, end_node, None)
    graph.add_edge(previous_node,end_node, weight=0)#cost)

print(f"Total Nodes: {len(graph.nodes)} \t Total Edges: {len(graph.edges)}")

shortest_paths = nx.all_shortest_paths(graph, start_node, end_node, weight="weight")
for path in shortest_paths:
    cost = 0
    prev_node = None
    for node in path:
        print(f"  {node.fingering}")
        if prev_node is not None:# and node is not end_node:
            cost += get_node_transition_cost(prev_node, node, None)
        prev_node = node
    print(f"cost: {cost}")
    
            


