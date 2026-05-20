import math

def agent(observation, configuration):
    maxSpeed = configuration.shipSpeed
    angular_velocity = observation.angular_velocity
    me = observation.player
    my_planets = [p for p in observation.planets if p[1] == me]
    target_planets = [p for p in observation.planets if p[1] != me]
    enemy_fleets = [f for f in observation.fleets if f[1] != me]
    
    actions = []
    
    reserved_ships = {p[0]: 0 for p in my_planets}
    
    for f in enemy_fleets:
        fx, fy = f[2], f[3]
        f_angle = f[4]
        f_ships = f[6]
        
        for p in my_planets:
            px, py = p[2], p[3]
            angle_to_planet = math.atan2(py - fy, px - fx)
            angle_diff = abs((f_angle - angle_to_planet + math.pi) % (2 * math.pi) - math.pi)
            if angle_diff < 0.2: 
                dist = math.hypot(px - fx, py - fy)
                speed = 1.0 + (maxSpeed - 1.0) * ((math.log(max(1, f_ships)) / math.log(1000)) ** 1.5)
                eta = dist / speed
                
                future_garrison = p[5] + p[6] * int(eta)
                if future_garrison < f_ships:
                    reserved_ships[p[0]] += f_ships
                else:
                    reserved_ships[p[0]] = max(reserved_ships[p[0]], int(f_ships - p[6] * eta))

    def predict_position(planet, dt):
        x, y = planet[2], planet[3]
        radius = math.hypot(x - 50, y - 50)
        if radius + planet[4] < 50:
            angle = math.atan2(y - 50, x - 50)
            angle += angular_velocity * dt
            return 50 + radius * math.cos(angle), 50 + radius * math.sin(angle)
        return x, y

    def compute_intercept(p, t, ships):
        speed = 1.0 + (maxSpeed - 1.0) * ((math.log(max(1, ships)) / math.log(1000)) ** 1.5)
        dt = 0
        for _ in range(10):
            tx, ty = predict_position(t, dt)
            dist = math.hypot(tx - p[2], ty - p[3])
            dt = dist / speed
        tx, ty = predict_position(t, dt)
        return math.atan2(ty - p[3], tx - p[2]), dt

    def path_intersects_sun(px, py, tx, ty):
        dx = tx - px
        dy = ty - py
        length = math.hypot(dx, dy)
        if length == 0: return False
        t = ((50 - px) * dx + (50 - py) * dy) / (length * length)
        if t < 0 or t > 1:
            dist1 = math.hypot(px - 50, py - 50)
            dist2 = math.hypot(tx - 50, ty - 50)
            return min(dist1, dist2) < 10
        else:
            cx = px + t * dx
            cy = py + t * dy
            return math.hypot(cx - 50, cy - 50) < 10

    comet_ids = set(observation.get("comet_planet_ids", []))

    for p in my_planets:
        available_ships = p[5] - reserved_ships[p[0]]
        available_ships = max(0, available_ships - 3) 
        
        if available_ships > 25: 
            best_target = None
            best_score = -99999
            best_angle = 0
            best_ships = 0
            
            for t in target_planets:
                if t[0] in comet_ids: continue 
                
                for fraction in [1.0, 0.5]:
                    ships_to_send = int(available_ships * fraction)
                    if ships_to_send <= 0: continue
                    
                    angle, dt = compute_intercept(p, t, ships_to_send)
                    tx, ty = predict_position(t, dt)
                    
                    if path_intersects_sun(p[2], p[3], tx, ty):
                        continue
                        
                    future_garrison = t[5]
                    if t[1] != -1:
                        future_garrison += t[6] * int(dt)
                        
                    if ships_to_send > future_garrison + 3: 
                        
                        enemy_bonus = 1.5 if t[1] != -1 else 1.0
                        score = (t[6] * enemy_bonus) / max(1, dt)
                        
                        if score > best_score:
                            best_score = score
                            best_target = t
                            best_angle = angle
                            best_ships = ships_to_send
                            
            if best_target:
                actions.append([p[0], best_angle, best_ships])
                reserved_ships[p[0]] += best_ships
                
    return actions
