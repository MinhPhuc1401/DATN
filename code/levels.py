LEVEL_DEFINITIONS = [
    # Level 1: 15 skeletons
    {
        'specific_enemies': [
            ('skeleton', 15)  # 15 skeleton enemies
        ],
        'random_enemies_config': None,
        'is_boss_level': False
    },
    # Level 2: 15 bats
    {
        'specific_enemies': [
            ('bat', 15)  # 15 bat enemies
        ],
        'random_enemies_config': None,
        'is_boss_level': False
    },
    # Level 3: 15 blobs
    {
        'specific_enemies': [
            ('blob', 15)  # 15 blob enemies
        ],
        'random_enemies_config': None,
        'is_boss_level': False
    },
    # Level 4: Boss only
    {
        'specific_enemies': None,
        'random_enemies_config': None,
        'is_boss_level': True  # Only boss fight
    }
]

TOTAL_LEVELS = len(LEVEL_DEFINITIONS)

def get_level_data(level_number):
    if 1 <= level_number <= TOTAL_LEVELS:
        return LEVEL_DEFINITIONS[level_number - 1]
    else:
        print(f"Warning: Level {level_number} data is not defined. No enemies will be spawned for this level.")
        return {
            'specific_enemies': None,
            'random_enemies_config': None,
            'is_boss_level': False
        }

