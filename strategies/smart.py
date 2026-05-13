from environment import TerrainType, AntPerception
from ant import AntAction, AntStrategy
from common import Direction
from collections import deque # for BFS
import random


class SmartStrategy(AntStrategy):
    """
    combines memory (cognitive map + BFS shortest path) with
    pheromones

    """

    DEPOSIT_EVERY = 3              
    PHEROMONE_FOLLOW_PROB = 0.75 

    def __init__(self):
        self.states = {}

    def decide_action(self, perception: AntPerception) -> AntAction:
        """Decide an action based on current perception"""
        ant_id = perception.ant_id
        state = self._get_states(ant_id, perception)
        self._update_state(state, perception)

        pos = state["pos"]
        current = perception.visible_cells.get((0, 0))

        
        if not perception.has_food and current == TerrainType.FOOD:
            state["path"] = [] 
            action = AntAction.PICK_UP_FOOD

        elif perception.has_food and current == TerrainType.COLONY:
            state["path"] = []
            action = AntAction.DROP_FOOD

        else:
            
            state["deposit_counter"] += 1
            if state["deposit_counter"] >= self.DEPOSIT_EVERY:
                state["deposit_counter"] = 0
                if perception.has_food:
                    action = AntAction.DEPOSIT_FOOD_PHEROMONE
                else:
                    action = AntAction.DEPOSIT_HOME_PHEROMONE

            elif perception.has_food:
                action = self._navigate_to(state, state["colony_pos"])
                if action is None:
                    action = self._explore(state, perception)

            else:
                if state["known_food"]:
                    nearest = min(
                        state["known_food"],
                        key=lambda f: max(abs(f[0] - pos[0]), abs(f[1] - pos[1])),
                    )
                    action = self._navigate_to(state, nearest)
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
        return self._explore(self._get_states(perception.ant_id, perception), perception)


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
                "visited": {(0, 0): 1}, # dict of visit counts (used by _explore)
                "path": [],
                "deposit_counter": 0,   # for pheromone interleave
            }
        return self.states[ant_id]

    def _update_state(self, state, perception):

        # position update if we moved forward last turn
        if state["last_action"] == AntAction.MOVE_FORWARD:
            dx, dy = Direction.get_delta(state["last_direction"])
            state["pos"] = (state["pos"][0] + dx, state["pos"][1] + dy)
            state["visited"][state["pos"]] = state["visited"].get(state["pos"], 0) + 1

        
        state["direction"] = perception.direction

        # always absorb perception 
        ax, ay = state["pos"] 
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
        t = perception.visible_cells.get((rdx, rdy))
        return t is not None and t != TerrainType.WALL


    def _action_toward(self, state, next_pos):
        """Move from state["pos"] toward next_pos next_pos must be adjacent."""
        terrain = state["known_map"].get(next_pos)
        if terrain == TerrainType.WALL:
            return None

        
        pos = state["pos"]
        dx = max(-1, min(1, next_pos[0] - pos[0]))
        dy = max(-1, min(1, next_pos[1] - pos[1]))

        target_dir = None
        for d in Direction:
            ddx, ddy = Direction.get_delta(d)
            if ddx == dx and ddy == dy:
                target_dir = d
                break
        
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
        """ Only known walls are blocked"""

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
                if terrain == TerrainType.WALL:
                    continue # unknown is OK (optimistic)

                new_path = path + [neighbor_pos]
                if neighbor_pos == goal:
                    return new_path

                seen.add(neighbor_pos)
                queue.append((neighbor_pos, new_path))

        return []


    def _navigate_to(self, state, goal):
        """Plan and step along a BFS path to goal. Returns None if no plan."""

        pos = state["pos"]
        if pos == goal:
            return None

        
        if state["path"] and state["path"][-1] != goal:
            state["path"] = []

        # drop cells we already stand on
        while state["path"] and state["path"][0] == pos:
            state["path"].pop(0)

        
        if state["path"] and state["known_map"].get(state["path"][0]) == TerrainType.WALL:
            state["path"] = []

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


    def _explore(self, state, perception):
        """Exploration step
        """

        pos = state["pos"]

        ptype = "home" if perception.has_food else "food"
        best_ph = self._strongest_pheromone_cell(perception, ptype)
        if best_ph is not None and random.random() < self.PHEROMONE_FOLLOW_PROB:
            rdx = max(-1, min(1, best_ph[0]))
            rdy = max(-1, min(1, best_ph[1]))
            immediate = (pos[0] + rdx, pos[1] + rdy)
            action = self._action_toward(state, immediate)
            if action is not None:
                return action

        deltas = [Direction.get_delta(d) for d in Direction]
        candidates = []
        for dx, dy in deltas:
            cell = (pos[0] + dx, pos[1] + dy)
            terrain = state["known_map"].get(cell)
            if terrain == TerrainType.WALL:
                continue
            v = state["visited"].get(cell, 0)
            candidates.append((v, dx, dy))

        if candidates:
            min_v = min(c[0] for c in candidates)
            best = [c for c in candidates if c[0] == min_v]
            cur_delta = Direction.get_delta(state["direction"])
            for c in best:
                if (c[1], c[2]) == cur_delta:
                    immediate = (pos[0] + c[1], pos[1] + c[2])
                    action = self._action_toward(state, immediate)
                    if action is not None:
                        return action
            _, dx, dy = random.choice(best)
            immediate = (pos[0] + dx, pos[1] + dy)
            action = self._action_toward(state, immediate)
            if action is not None:
                return action

        dx, dy = Direction.get_delta(state["direction"])
        fwd = perception.visible_cells.get((dx, dy))
        if fwd is not None and fwd != TerrainType.WALL and random.random() < 0.65:
            return AntAction.MOVE_FORWARD

        return random.choice([AntAction.TURN_LEFT, AntAction.TURN_RIGHT])



   