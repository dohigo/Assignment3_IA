from environment import TerrainType, AntPerception
from ant import AntAction, AntStrategy
from common import Direction
import random

class CooperativeStrategy(AntStrategy):
    
    def _get_state(self, ant_id):
        if ant_id not in self.states:
            self.states[ant_id] = {
                "deposit_turn": False
            }
        return self.states[ant_id]

    def _is_visible_and_clear(self, perception, rdx, rdy):
        """Check if ant can see the cell and it is not a wall"""
        t = perception.visible_cells.get((rdx, rdy))
        return t is not None and t != TerrainType.WALL

    def _move_toward_delta(self, perception, rdx, rdy):
        """return the action that moves the ant one step toward the relative offset (rdx, rdy). Turns to align first and then moves forward."""

        #because ant can see only 1,0,-1
        rdx = max(-1, min(1, rdx)) 
        rdy = max(-1, min(1, rdy))

        target_dir = None
        for d in Direction:
            ddx, ddy = Direction.get_delta(d)
            if ddx == rdx and ddy == rdy:
                target_dir = d
                break
        # in case (0,0)
        if target_dir is None:
            return random.choice([AntAction.TURN_LEFT, AntAction.TURN_RIGHT])

        current = perception.direction
        if current == target_dir:
            if not self._is_visible_and_clear(perception, rdx, rdy): # wall chek
                return random.choice([AntAction.TURN_LEFT, AntAction.TURN_RIGHT])
            return AntAction.MOVE_FORWARD

        diff = (target_dir.value - current.value) % 8 #clockwise or counter-clockwise turn

        if diff <= 4:
            return AntAction.TURN_RIGHT
        else:
            return AntAction.TURN_LEFT

    def _strongest_pheromone_cell(self, perception, pheromone_type):
        """Find the visible cell with the strongest pheromone of the given type"""

        if pheromone_type == "food":
            pmap = perception.food_pheromone
        else:
            pmap = perception.home_pheromone

        best_val = 0.5
        best_pos = None

        for (dx, dy), val in pmap.items():
            if (dx == 0) and (dy == 0):
                continue
            if not self._is_visible_and_clear(perception, dx, dy):
                continue
            if val > best_val:
                best_val = val
                best_pos = (dx, dy)
        
        return best_pos

    def _random_walk(self, perception):
        """Random walk mostly forward"""

        dx, dy = Direction.get_delta(perception.direction)
        if self._is_visible_and_clear(perception, dx, dy) and random.random() < 0.7: # 70% forward
            return AntAction.MOVE_FORWARD

        return random.choice([AntAction.TURN_LEFT, AntAction.TURN_RIGHT])



    def __init__(self):
        """Initialize the strategy with last action tracking"""
        self.states = {}



    def decide_action(self, perception: AntPerception) -> AntAction:
        """Decide an action based on current perception"""

        ant_id = perception.ant_id
        state = self._get_state(ant_id)
        current = perception.visible_cells.get((0, 0))

        if not perception.has_food and current == TerrainType.FOOD:
            return AntAction.PICK_UP_FOOD
        
        if perception.has_food and current == TerrainType.COLONY:
            return AntAction.DROP_FOOD

        # navigating and depositing pheromone alternatively
        if state["deposit_turn"]:
            state["deposit_turn"] = False
            if perception.has_food:
                return AntAction.DEPOSIT_FOOD_PHEROMONE
            else:
                return AntAction.DEPOSIT_HOME_PHEROMONE

        state["deposit_turn"] = True

        if perception.has_food:
            # Go home with food
            if perception.can_see_colony():
                dir_val = perception.get_colony_direction()
                dx, dy = Direction.get_delta(Direction(dir_val))
                return self._move_toward_delta(perception, dx, dy)

            best = self._strongest_pheromone_cell(perception, "home")
            if best is not None and random.random() < 0.85:
                return self._move_toward_delta(perception, best[0], best[1])

            return self._random_walk(perception)

        else:
            # Search for food
            if perception.can_see_food():
                dir_val = perception.get_food_direction()
                dx, dy = Direction.get_delta(Direction(dir_val))
                return self._move_toward_delta(perception, dx, dy)

            best = self._strongest_pheromone_cell(perception, "food")
            if best is not None and random.random() < 0.85:
                return self._move_toward_delta(perception, best[0], best[1])

            return self._random_walk(perception)





    
    def _decide_movement(self, perception: AntPerception) -> AntAction:
        """Decide which direction to move based on current state"""
        # TODO: Insert your code here

        random_direction = random.choice([AntAction.MOVE_FORWARD, AntAction.TURN_LEFT, AntAction.TURN_RIGHT])
        return random_direction  # Random movement for now, replace with actual logic
