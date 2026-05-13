from environment import TerrainType, AntPerception
from ant import AntAction, AntStrategy
from common import Direction
from collections import deque # for BFS
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

        # position update if moves
        if state["last_action"] == AntAction.MOVE_FORWARD:
            dx, dy = Direction.get_delta(state["last_direction"])
            state["pos"] = (state["pos"][0] + dx, state["pos"][1] + dy)
            state["visited"].add(state["pos"])

            state["direction"] = perception.direction

            ax, ay = state["pos"] # absolute position
            for (rdx, rdy), terrain in perception.visible_cells.items():
                abs_pos = (ax + rdx, ay + rdy)
                old = state["known_map"].get(abs_pos)
                state["known_map"][abs_pos] = terrain
                if terrain == TerrainType.FOOD:
                    state["known_food"].add(abs_pos)
                elif terrain == TerrainType.COLONY:
                    state["colony_pos"] = abs_pos
                elif old == TerrainType.FOOD and terrain != TerrainType.FOOD:
                    state["known_food"].discard(abs_pos)


    def _is_visible_and_clear(self, perception, rdx, rdy):
        """Check if ant can see the cell and it is not a wall"""
        t = perception.visible_cells.get((rdx, rdy))
        return t is not None and t != TerrainType.WALL


    def _action_toward(self, state, next_pos):
        """Move from state["pos"] toward next_pos"""
        terrain = state["known_map"].get(next_pos)
        if terrain is None or terrain == TerrainType.WALL:
            return None

        # offset computaion from current position to target position
        pos = state["pos"]
        dx = max(-1, min(1, next_pos[0] - pos[0]))
        dy = max(-1, min(1, next_pos[1] - pos[1]))

        target_dir = None
        for d in Direction:
            ddx, ddy = Direction.get_delta(d)
            if ddx == dx and ddy == dy:
                target_dir = d
                break
        # in case (0,0)
        if target_dir is None:
            return random.choice([AntAction.TURN_LEFT, AntAction.TURN_RIGHT])

        current = state["direction"]
        if current == target_dir:
            return AntAction.MOVE_FORWARD

        diff = (target_dir.value - current.value) % 8 #clockwise or counter-clockwise turn

        if diff <= 4:
            return AntAction.TURN_RIGHT
        else:
            return AntAction.TURN_LEFT

    def _bfs_path(self, state, start, goal):

        if start == goal:
            return []

        queue = deque([(start, [])])
        seen = {start}

        while queue:
            pos, path = queue.popleft()

        for d in Direction: # 8 directions
            dx, dy = Direction.get_delta(d)
            neighbor_pos = (pos[0] + dx, pos[1] + dy)

            if neighbor_pos in seen:
                continue

            terrain = state["known_map"].get(neighbor_pos)
            if terrain is None or terrain == TerrainType.WALL:
                continue

            new_path = path + [neighbor_pos]
            if neighbor_pos == goal:
                return new_path
            
            seen.add(neighbor_pos)
            queue.append((neighbor_pos, new_path))


        return []

    def _navigate_to(self, state, goal):

        pos = state["pos"]
        if pos == goal:
            return None 

        #
        if state["path"] and state["path"][-1] != goal: 
            state["path"] = []

        while state["path"] and state["path"][0] == pos:
            state["path"].pop(0)

        if not state["path"]:
            state["path"] = self._bfs_path(state, pos, goal)

        if not state["path"]:
            return None
        
        next_pos = state["path"][0]
        action = self._action_toward(state, next_pos)

        if action == AntAction.MOVE_FORWARD:
            state["path"].pop(0)
        elif action is None:
            state["path"] = []
            return None

        return action

    def _explore(self, state, perception):

        pos = state["pos"]

        best = None
        best_dist = float("inf")
        for (rdx, rdy), terrain in perception.visible_cells.items():
            if terrain == TerrainType.WALL:
                continue
            abs_pos = (pos[0] + rdx, pos[1] + rdy)
            if abs_pos not in state["visited"]:
                dist = abs(rdx) + abs(rdy)
                if dist < best_dist:
                    best_dist = dist
                    best = abs_pos
        
        if best is not None:
            action = self._action_toward(state, best)
            if action is not None:
                return action

        dx, dy = Direction.get_delta(state["direction"])
        fwd = perception.visible_cells.get((dx, dy))
        if fwd is not None and fwd != TerrainType.WALL and random.random() < 0.65:
            return AntAction.MOVE_FORWARD

        return random.choice([AntAction.TURN_LEFT, AntAction.TURN_RIGHT])
        


    def __init__(self):
        """Initialize the strategy with last action tracking"""
        self.states = {}




    def decide_action(self, perception: AntPerception) -> AntAction:
        """Decide an action based on current perception"""
        ant_id = perception.ant_id
        state = self._get_states(ant_id, perception)
        self._update_state(state, perception)

        pos = state["pos"]
        current = perception.visible_cells.get((0, 0))

        if not perception.has_food and current == TerrainType.FOOD:
            state["path"] = [] # clean, new goal go colony
            return AntAction.PICK_UP_FOOD
        
        if perception.has_food and current == TerrainType.COLONY:
            state["path"] = []
            return AntAction.DROP_FOOD

        if perception.has_food:
            action = self._navigate_to(state, state["colony_pos"])
            if action is  None:
                action = self._explore(state, perception)

        else:
            if state["known_food"]:
                nearest = min(
                    state["known_food"],
                    key=lambda f: abs(f[0] - pos[0]) + abs(f[1] - pos[1]),
                )
                action =self._navigate_to(state, nearest)
                if action is None:
                    state["known_food"].discard(nearest)
                    action = self._explore(state, perception)
            else:
                action = self._explore(state, perception)

        state["last_direction"] = state["direction"]
        state["last_action"] = action
        return action

        
        







    def _decide_movement(self, perception: AntPerception) -> AntAction:
        """Decide which direction to move based on current state"""
        # TODO: Insert your code here

        random_direction = random.choice([AntAction.MOVE_FORWARD, AntAction.TURN_LEFT, AntAction.TURN_RIGHT])
        return random_direction  # Random movement for now, replace with actual logic