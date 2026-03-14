import json

with open('data/historical_races/races_00000-00999.json', 'r') as f:
    races = json.load(f)
    print(races)
with open('data/test_cases/inputs/test_001.json', 'r') as f:
    test_case = json.load(f)

with open('data/test_cases/expected_outputs/test_001.json', 'r') as f:
    expected = json.load(f)
