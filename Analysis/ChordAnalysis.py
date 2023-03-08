# -*- coding: utf-8 -*-
"""
Created on Mon Mar  6 13:27:44 2023

@author: andre
"""

def max_fingers_per_fret(fingering, positions):
    frets = list(set(positions))
    max_fingers_used = 0
    for fret in frets:
        if fret=='x':
            continue
        fret_occurances = [i for i, p in enumerate(positions) if p == fret]
        fingers_used = list(map(fingering.__getitem__,fret_occurances))
        distinct_fingers_used = set(fingers_used)
        num_fingers_used = len(distinct_fingers_used)
        if num_fingers_used > max_fingers_used:
            max_fingers_used = num_fingers_used
    return max_fingers_used
        
def get_barre_count(fingering, positions):
    barre_count = 0
    for finger in range(1,5):
        finger_occurances = [i for i, f in enumerate(fingering) if str(f) == str(finger)]
        if len(finger_occurances) > 1:
            barre_count+=1;
    return barre_count;
    
def get_fret_range(fingering, positions):
    frets = [int(p) for i, p in enumerate(positions) if (p.isnumeric() and int(p) != 0)]
    if not frets:
        return 0
    print(f"{frets}: {max(frets) - min(frets)}")
    return max(frets) - min(frets)

def get_highest_use_of_finger(finger,fingering):
    try: 
        return 6-fingering.index(str(finger))
    except:
        return 0

import json

chords_file = open("chords.json")
output_file = open("chords_analysis.csv", 'w')
output_file.write("Chord; Position; Fingering; Max Fingers Required; Number of Barres; Fret Range; Highest Ring Finger; Highest Pinky Finger\n")

chords_json = json.load(chords_file)

for chord in chords_json:
    min_fingers_in_chord = 5
    for chord_position in chords_json[chord]:
        min_fingers_required = 5
        worst_fingering = chord_position['fingerings'][0]
        bullet = ' ';
        for fingering in chord_position['fingerings']:
            max_fingers_required = max_fingers_per_fret(fingering,chord_position['positions'])
            if max_fingers_required < min_fingers_required:
                min_fingers_required = max_fingers_required
                worst_fingering = fingering
            if max_fingers_required < min_fingers_in_chord:
                min_fingers_in_chord = max_fingers_required
            output_file.write(f"{chord}; {chord_position['positions']}; {fingering}; {max_fingers_required}; {get_barre_count(fingering, chord_position['positions'])}; {get_fret_range(fingering,chord_position['positions'])}; {get_highest_use_of_finger(3,fingering)}; {get_highest_use_of_finger(4,fingering)}\n")
        if min_fingers_required > 2:
            bullet = '!'
        #print(f"{bullet} {min_fingers_required} Fingers Required for {chord} in positions {chord_position['positions']}: {worst_fingering}")
    print(f"{chord}\t: {min_fingers_in_chord}")
    
chords_file.close();
output_file.close();