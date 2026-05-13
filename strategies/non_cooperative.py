from environment import TerrainType, AntPerception
from ant import AntAction, AntStrategy
from common import Direction
from collections import deque
import random


class NonCooperativeStrategy(AntStrategy):
    
    def _get_states(self, ant_id, perception):
        """Get or create the state of the ant as dictionary"""
        if ant_id not in self.states:
            self.states[ant_id] = {
                "pos": (0, 0),
                "direction": perception.direction,
                "last_direction": perception.direction,
                "last_action": None,
                "known_map": {(0, 0): TerrainType.COLONY},
                "known_food": set(),
                "colony_pos": (0, 0),
                "visited": {(0, 0)},
                "path": [],
            }
        return self.states[ant_id]

    def _update_state(self, state, perception):
        
        return





    def __init__(self):
        """Initialize the strategy with last action tracking"""
        self.states = {}




    def decide_action(self, perception: AntPerception) -> AntAction:
        """Decide an action based on current perception"""

        # TODO: Insert your code here
        
        return self._decide_movement(perception)




    def _decide_movement(self, perception: AntPerception) -> AntAction:
        """Decide which direction to move based on current state"""
        # TODO: Insert your code here

        random_direction = random.choice([AntAction.MOVE_FORWARD, AntAction.TURN_LEFT, AntAction.TURN_RIGHT])
        return random_direction  # Random movement for now, replace with actual logic