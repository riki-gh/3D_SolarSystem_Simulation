from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import time

# ==============================================================================
#   SECTION 1: CONFIGURATION & CONSTANTS
# ==============================================================================


WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
WINDOW_TITLE = b"Advanced 3D Solar System Simulator - Procedural Edition"


PI = 3.14159265358979323846
DEG_TO_RAD = PI / 180.0
RAD_TO_DEG = 180.0 / PI


SIM_SPEED_DEFAULT = 0.5
MAX_TRAIL_LENGTH = 100
ASTEROID_COUNT = 600

COLOR_WHITE = (1.0, 1.0, 1.0)
COLOR_BLACK = (0.0, 0.0, 0.0)
COLOR_RED   = (1.0, 0.0, 0.0)
COLOR_GREEN = (0.0, 1.0, 0.0)
COLOR_BLUE  = (0.0, 0.0, 1.0)
COLOR_YELLOW= (1.0, 1.0, 0.0)
COLOR_CYAN  = (0.0, 1.0, 1.0)
COLOR_MAGENTA= (1.0, 0.0, 1.0)
COLOR_GREY  = (0.5, 0.5, 0.5)


FONT_HEADER = GLUT_BITMAP_HELVETICA_18
FONT_BODY = GLUT_BITMAP_HELVETICA_12

# ==============================================================================
#   SECTION 2: MATH LIBRARY (Vector3 & Matrix Helpers)
# ==============================================================================

class Vector3:

    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

   
    def __add__(self, v):
        return Vector3(self.x + v.x, self.y + v.y, self.z + v.z)

    def __sub__(self, v):
        return Vector3(self.x - v.x, self.y - v.y, self.z - v.z)

    def __mul__(self, s):
        return Vector3(self.x * s, self.y * s, self.z * s)

    def __truediv__(self, s):
        if s == 0: return Vector3(0, 0, 0)
        return Vector3(self.x / s, self.y / s, self.z / s)

    def __neg__(self):
        return Vector3(-self.x, -self.y, -self.z)
    
    def __eq__(self, other):
        return abs(self.x - other.x) < 0.001 and \
               abs(self.y - other.y) < 0.001 and \
               abs(self.z - other.z) < 0.001

    def __str__(self):
        return f"Vec3({self.x:.2f}, {self.y:.2f}, {self.z:.2f})"

    
    def dot(self, v):
       
        return self.x * v.x + self.y * v.y + self.z * v.z

    def cross(self, v):
       
        return Vector3(
            self.y * v.z - self.z * v.y,
            self.z * v.x - self.x * v.z,
            self.x * v.y - self.y * v.x
        )

    def magnitude(self):
       
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalized(self):
       
        m = self.magnitude()
        if m > 0.0: return self / m
        return Vector3(0, 0, 0)
    
    def distance_to(self, other):
        
        return (self - other).magnitude()

    def lerp(self, target, t):
        """Linear interpolation """
        t = max(0.0, min(1.0, t))
        return self + (target - self) * t

    def rotate_around_axis(self, axis, angle_deg):
        """
        Rodrigues' Rotation Formula.
        Rotates this vector around an arbitrary normalized axis.
        """
        rad = angle_deg * DEG_TO_RAD
        k = axis.normalized()
        cos_t = math.cos(rad)
        sin_t = math.sin(rad)
        
        # v_rot = v*cos(t) + (k x v)*sin(t) + k*(k.v)*(1-cos(t))
        term1 = self * cos_t
        term2 = k.cross(self) * sin_t
        term3 = k * (k.dot(self) * (1 - cos_t))
        
        return term1 + term2 + term3


# ==============================================================================
#   SECTION 3: CAMERA SYSTEM (Physics-Based)
# ==============================================================================

class Camera:
  
    def __init__(self, pos=Vector3(0, 1000, 1500), target=Vector3(0, 0, 0)):
        self.position = pos
        self.target_look_at = (target - pos).normalized()
        
        
        self.lookAt = self.target_look_at
        self.up = Vector3(0, 1, 0)
        self.right = Vector3(1, 0, 0)
        
        
        self.velocity = Vector3(0,0,0)
        self.move_speed_base = 15.0
        self.rot_speed_base = 2.0
        self.friction = 0.85
        
        self.update_ortho_vectors()

    def update_ortho_vectors(self):
        
        self.right = self.lookAt.cross(self.up).normalized()
        self.up = self.right.cross(self.lookAt).normalized()

    def update_physics(self):
        
        if self.velocity.magnitude() > 0.01:
            self.position = self.position + self.velocity
            self.velocity = self.velocity * self.friction # Damping
        else:
            self.velocity = Vector3(0,0,0)

    
    def add_velocity(self, direction_vec):
        self.velocity = self.velocity + (direction_vec * self.move_speed_base * 0.2)

    def move_forward(self):  self.add_velocity(self.lookAt)
    def move_backward(self): self.add_velocity(-self.lookAt)
    def move_left(self):     self.add_velocity(-self.right)
    def move_right(self):    self.add_velocity(self.right)
    def move_up(self):       self.add_velocity(self.up)
    def move_down(self):     self.add_velocity(-self.up)

    
    def look_yaw(self, angle):
        
        self.lookAt = self.lookAt.rotate_around_axis(self.up, angle * self.rot_speed_base)
        self.update_ortho_vectors()

    def look_pitch(self, angle):
        
        self.lookAt = self.lookAt.rotate_around_axis(self.right, angle * self.rot_speed_base)
        self.update_ortho_vectors()

    def roll(self, angle):
        
        self.up = self.up.rotate_around_axis(self.lookAt, angle * self.rot_speed_base)
        self.update_ortho_vectors()

    
    def orbit_vertical(self, angle):
        """Moves the camera up/down physically while keeping focus on the center (0,0,0)."""
        ref_point = Vector3(0,0,0)
        # Vector from center to camera
        radius_vec = self.position - ref_point
        
        # Rotate this radius vector around the camera's RIGHT axis
        
        new_radius = radius_vec.rotate_around_axis(self.right, angle * self.rot_speed_base)
        
        self.position = ref_point + new_radius
        
      
        self.lookAt = (-new_radius).normalized()
        self.update_ortho_vectors()

    def get_view_matrix(self):
        center = self.position + self.lookAt
        return (self.position.x, self.position.y, self.position.z,
                center.x, center.y, center.z,
                self.up.x, self.up.y, self.up.z)


# ==============================================================================
#   SECTION 4: PROCEDURAL GENERATION & DRAWING ENGINE
# ==============================================================================

class PlanetSurfaceGenerator:
    
    @staticmethod
    def get_color(type_str, lat, lng, base_color):
       
        r, g, b = base_color
        
        if type_str == "gas_giant_bands":
            # Jupiter/Saturn style bands
            
            band_freq = 10.0
            intensity = 0.8 + 0.2 * math.sin(lat * band_freq)
            #turbulence
            intensity += 0.05 * math.sin(lng * 5.0)
            return (r * intensity, g * intensity, b * intensity)
            
        elif type_str == "rocky_cratered":
            # Mercury/Moon style
            # Random noise 
            noise = math.sin(lat*20) * math.cos(lng*20)
            intensity = 0.8 + 0.2 * noise
            # (dark spots)
            if abs(math.sin(lat*5 + lng*5)) > 0.95:
                intensity *= 0.6
            return (r * intensity, g * intensity, b * intensity)
            
        elif type_str == "earth_like":
            # Blue oceans, Green/Brown land
            
            noise = math.sin(lat*2) + math.sin(lng*3) + 0.5*math.cos(lat*10)
            if noise > 0.5:
                # Land (Green)
                return (0.1, 0.6 + 0.1*noise, 0.1) # Greenish
            else:
                # Ocean (Blue)
                return (0.0, 0.2 + 0.1*abs(noise), 0.8) 
                
        elif type_str == "sun":
            
            return (1.0, 0.8 + 0.2*math.sin(lat*10), 0.0)
            
        else:
            
            return base_color

def draw_procedural_sphere(radius, surface_type, base_color, center_pos, rotation_deg, spin_axis=Vector3(0,0,1)):

    slices = 24
    stacks = 24
    
    
    sun_pos = Vector3(0,0,0)

    # Rotation Matrix for planet spin
   

    for i in range(stacks):
        lat0 = PI * (-0.5 + float(i) / stacks)
        z0 = math.sin(lat0) * radius
        zr0 = math.cos(lat0) * radius
        
        lat1 = PI * (-0.5 + float(i + 1) / stacks)
        z1 = math.sin(lat1) * radius
        zr1 = math.cos(lat1) * radius
        
        glBegin(GL_QUADS)
        for j in range(slices):
            lng = 2 * PI * float(j) / slices
            x0 = math.cos(lng) * zr0
            y0 = math.sin(lng) * zr0
            
            lng1 = 2 * PI * float(j + 1) / slices
            x1 = math.cos(lng1) * zr0
            y1 = math.sin(lng1) * zr0
            
            x2 = math.cos(lng1) * zr1
            y2 = math.sin(lng1) * zr1
            
            x3 = math.cos(lng) * zr1
            y3 = math.sin(lng) * zr1
            
           
            verts = [
                (Vector3(x0, y0, z0), lat0, lng),
                (Vector3(x1, y1, z0), lat0, lng1),
                (Vector3(x2, y2, z1), lat1, lng1),
                (Vector3(x3, y3, z1), lat1, lng)
            ]
            
            for v_local, v_lat, v_lng in verts:
                
                v_rot = v_local.rotate_around_axis(spin_axis, rotation_deg)

                
                v_world = center_pos + v_rot

                
                if radius != 0:
                    z_ratio = max(-1.0, min(1.0, v_rot.z / radius))
                    lat_rot = math.asin(z_ratio)
                else:
                    lat_rot = 0.0

                lng_rot = math.atan2(v_rot.y, v_rot.x)
                if lng_rot < 0:
                    lng_rot += 2 * PI

                
                c_r, c_g, c_b = PlanetSurfaceGenerator.get_color(surface_type, lat_rot, lng_rot, base_color)

                # 2. Lighting Calculation 
                intensity = 1.0
                if surface_type != "sun":
                    
                    normal = v_rot.normalized()
                    
                    to_sun = (sun_pos - v_world).normalized()
                    
                    dot = normal.dot(to_sun)
                    diffuse = max(0.0, dot)
                    ambient = 0.04
                    intensity = ambient + (1.0 - ambient) * diffuse

                glColor3f(c_r * intensity, c_g * intensity, c_b * intensity)
                glVertex3f(v_world.x, v_world.y, v_world.z)
                
        glEnd()

def draw_ring_system(inner_r, outer_r, center_pos, tilt_x, tilt_y):
    """
    Draws a flat ring for Saturn/Uranus.
    """
    slices = 40
    step = (2 * PI) / slices
    
    glPushMatrix()
    glTranslatef(center_pos.x, center_pos.y, center_pos.z)
    glRotatef(tilt_x, 1, 0, 0) 
    glRotatef(tilt_y, 0, 1, 0)
    
    glBegin(GL_QUADS)
    glColor3f(0.6, 0.5, 0.4) 
    
    for i in range(slices):
        angle = i * step
        next_angle = (i+1) * step
        
        
        x1 = math.cos(angle) * inner_r
        y1 = math.sin(angle) * inner_r
        
        
        x2 = math.cos(angle) * outer_r
        y2 = math.sin(angle) * outer_r
        
       
        x3 = math.cos(next_angle) * outer_r
        y3 = math.sin(next_angle) * outer_r
        
        
        x4 = math.cos(next_angle) * inner_r
        y4 = math.sin(next_angle) * inner_r
        
        glVertex3f(x1, y1, 0)
        glVertex3f(x2, y2, 0)
        glVertex3f(x3, y3, 0)
        glVertex3f(x4, y4, 0)
        
    glEnd()
    glPopMatrix()


# ==============================================================================
#   SECTION 5: CELESTIAL OBJECT CLASSES
# ==============================================================================

class CelestialBody:
    def __init__(self, name, size, orbit_r, orbit_speed, color, type_str="solid", parent=None, inclination=0.0, axial_tilt=0.0):
        self.name = name
        self.size = size
        self.orbit_radius = orbit_r
        self.orbit_speed = orbit_speed
        self.color = color
        self.type_str = type_str
        self.parent = parent
        self.inclination = inclination # Degrees tilt from z=0 plane
        
       
        self.angle = random.uniform(0, 360)
        self.rotation_angle = 0.0
        self.rotation_speed = random.uniform(0.5, 5.0) 
        self.position = Vector3(0,0,0)
        self.trail = []
        
        self.axial_tilt = axial_tilt
        tilt_rad = self.axial_tilt * DEG_TO_RAD
       
        self.axial_axis = Vector3(0.0, -math.sin(tilt_rad), math.cos(tilt_rad)).normalized()
        
        
        self.update(0)

    def update(self, dt):
        
        self.angle += self.orbit_speed * dt
        if self.angle > 360: self.angle -= 360
        
        
        self.rotation_angle += self.rotation_speed * dt
        
       
        rad = self.angle * DEG_TO_RAD
        inc_rad = self.inclination * DEG_TO_RAD
        
        
        x = math.cos(rad) * self.orbit_radius
        y = math.sin(rad) * self.orbit_radius
        z = 0
        
        # Apply inclination (rotate around X axis slightly)
        # New Y = Y cos(i) - Z sin(i)
        # New Z = Y sin(i) + Z cos(i)
        y_inc = y * math.cos(inc_rad)
        z_inc = y * math.sin(inc_rad)
        
        if self.parent:
            
            self.position = self.parent.position + Vector3(x, y_inc, z_inc)
        else:
            
            self.position = Vector3(x, y_inc, z_inc)
            
       
        if len(self.trail) == 0 or self.position.distance_to(Vector3(*self.trail[-1])) > 2.0:
            self.trail.append((self.position.x, self.position.y, self.position.z))
            if len(self.trail) > MAX_TRAIL_LENGTH:
                self.trail.pop(0)

    def draw(self, is_selected):
        
        if len(self.trail) > 2:
            glLineWidth(1.0)
            glBegin(GL_LINE_STRIP)
            alpha = 0.1
            for i, p in enumerate(self.trail):
                
                frac = i / len(self.trail)
                glColor3f(self.color[0]*frac, self.color[1]*frac, self.color[2]*frac)
                glVertex3f(p[0], p[1], p[2])
            glEnd()
            
        
        draw_procedural_sphere(self.size, self.type_str, self.color, self.position, self.rotation_angle, self.axial_axis)

        # Draw Selection Box
        if is_selected:
            glColor3f(1, 1, 1)
            glPushMatrix()
            glTranslatef(self.position.x, self.position.y, self.position.z)
            glutWireCube(self.size * 2.2)
            
            self.draw_label()
            glPopMatrix()

    def draw_label(self):
        
        glRasterPos3f(0, self.size * 1.5, 0)
        for c in self.name:
            glutBitmapCharacter(FONT_BODY, ord(c))


class AsteroidBelt:
  
    def __init__(self, inner_r, outer_r, count):
        self.asteroids = []
        for _ in range(count):
            angle = random.uniform(0, 360)
            dist = random.uniform(inner_r, outer_r)
            speed = random.uniform(0.2, 0.4)
            
            z_offset = random.uniform(-10, 10)
            self.asteroids.append({
                'angle': angle,
                'dist': dist,
                'speed': speed,
                'z': z_offset,
                'size': random.uniform(0.5, 1.5)
            })

    def update(self, dt):
        for ast in self.asteroids:
            ast['angle'] += ast['speed'] * dt

    def draw(self):
        glPointSize(1.0)
        glBegin(GL_POINTS)
        glColor3f(0.6, 0.6, 0.6)
        for ast in self.asteroids:
            rad = ast['angle'] * DEG_TO_RAD
            x = math.cos(rad) * ast['dist']
            y = math.sin(rad) * ast['dist']
            glVertex3f(x, y, ast['z'])
        glEnd()


class Starfield:
   
    def __init__(self, count=1000):
        self.stars = []
        for _ in range(count):
            
            u = random.uniform(0, 1)
            v = random.uniform(0, 1)
            theta = 2 * PI * u
            phi = math.acos(2 * v - 1)
            r = random.uniform(2000, 3000)
            
            x = r * math.sin(phi) * math.cos(theta)
            y = r * math.sin(phi) * math.sin(theta)
            z = r * math.cos(phi)
            
            self.stars.append({'pos': (x,y,z), 'phase': random.uniform(0, PI)})

    def draw(self):
        t = time.time()
        glPointSize(1.5)
        glBegin(GL_POINTS)
        for s in self.stars:
            
            brightness = 0.5 + 0.5 * math.sin(t * 2 + s['phase'])
            glColor3f(brightness, brightness, brightness)
            glVertex3f(*s['pos'])
        glEnd()


# ==============================================================================
#   SECTION 6: UI & HUD SYSTEM
# ==============================================================================

class ConsoleLog:
  
    def __init__(self):
        self.messages = []
        self.max_msgs = 5
        self.add_message("System Initialized.")
        self.add_message("Welcome to Solar Sim v2.0")

    def add_message(self, text):
        timestamp = time.strftime("%H:%M:%S")
        self.messages.append(f"[{timestamp}] {text}")
        if len(self.messages) > self.max_msgs:
            self.messages.pop(0)

    def draw(self):
        y_start = 100
        glColor3f(0.7, 0.7, 0.7)
        for msg in self.messages:
            glRasterPos2f(20, y_start)
            for c in msg:
                glutBitmapCharacter(FONT_BODY, ord(c))
            y_start -= 15


def draw_hud_text(x, y, text, font=FONT_BODY, color=COLOR_WHITE):
    glColor3f(*color)
    glRasterPos2f(x, y)
    for c in text:
        glutBitmapCharacter(font, ord(c))


# ==============================================================================
#   SECTION 7: MAIN APPLICATION LOGIC
# ==============================================================================


camera = None
bodies = []
asteroid_belt = None
starfield = None
console = None

selected_index = -1
sim_speed = SIM_SPEED_DEFAULT
is_paused = False

def init_world():
    global camera, bodies, asteroid_belt, starfield, console
    
    
    camera = Camera(pos=Vector3(0, 600, 1200))
    console = ConsoleLog()
    
    
    starfield = Starfield(1000)
    
    # Solar System Creation
    # Syntax: Name, Size, OrbitR, OrbitSpeed, Color, Type, Parent, Inclination
    
    # Sun
    sun = CelestialBody("Sun", 70, 0, 0, COLOR_YELLOW, "sun", axial_tilt=7.25)
    bodies.append(sun)
    
    # Mercury
    bodies.append(CelestialBody("Mercury", 8, 120, 2.5, (0.7,0.7,0.7), "rocky_cratered", inclination=7.0, axial_tilt=0.03))
    
    # Venus
    bodies.append(CelestialBody("Venus", 14, 180, 1.8, (0.9,0.7,0.2), "solid", inclination=3.4, axial_tilt=177.4))
    
    # Earth & Moon
    earth = CelestialBody("Earth", 15, 260, 1.2, (0.2,0.5,1.0), "earth_like", inclination=0.0, axial_tilt=23.5)
    bodies.append(earth)
    bodies.append(CelestialBody("Moon", 4, 30, 8.0, (0.8,0.8,0.8), "rocky_cratered", parent=earth, inclination=5.1, axial_tilt=6.68))
    
    # Mars
    bodies.append(CelestialBody("Mars", 12, 350, 0.9, (1.0,0.3,0.1), "rocky_cratered", inclination=1.8, axial_tilt=25.19))
    
    # Asteroid Belt (Visual only, no interaction)
    asteroid_belt = AsteroidBelt(400, 550, ASTEROID_COUNT)
    
    # Jupiter & Galilean Moons
    jupiter = CelestialBody("Jupiter", 40, 650, 0.5, (0.8,0.6,0.4), "gas_giant_bands", inclination=1.3, axial_tilt=3.13)
    bodies.append(jupiter)
    bodies.append(CelestialBody("Io", 3, 50, 6.0, (1,1,0), "solid", parent=jupiter, axial_tilt=0.05))
    bodies.append(CelestialBody("Europa", 3, 60, 5.0, (0.9,0.9,1), "solid", parent=jupiter, axial_tilt=0.1))
    bodies.append(CelestialBody("Ganymede", 4, 75, 4.0, (0.6,0.6,0.6), "solid", parent=jupiter, axial_tilt=0.3))
    bodies.append(CelestialBody("Callisto", 4, 90, 3.0, (0.5,0.5,0.5), "solid", parent=jupiter, axial_tilt=0.2))
    
    # Saturn & Titan
    saturn = CelestialBody("Saturn", 35, 900, 0.3, (0.9,0.8,0.6), "gas_giant_bands", inclination=2.5, axial_tilt=26.73)
    bodies.append(saturn)
    bodies.append(CelestialBody("Titan", 4, 55, 4.0, (1,0.6,0.2), "solid", parent=saturn, axial_tilt=0.3))
    
    # Uranus
    bodies.append(CelestialBody("Uranus", 22, 1100, 0.2, (0.5,0.8,0.9), "gas_giant_bands", inclination=0.8, axial_tilt=97.77))
    
    # Neptune
    bodies.append(CelestialBody("Neptune", 20, 1300, 0.1, (0.2,0.3,0.8), "solid", inclination=1.8, axial_tilt=28.32))

    
    rot_map = {
        'Sun': 14.0,
        'Mercury': 0.6,
        'Venus': -0.2,   
        'Earth': 30.0,
        'Moon': 5.0,
        'Mars': 24.0,
        'Jupiter': 120.0,
        'Io': 90.0,
        'Europa': 60.0,
        'Ganymede': 40.0,
        'Callisto': 30.0,
        'Saturn': 100.0,
        'Titan': 30.0,
        'Uranus': 60.0,
        'Neptune': 40.0
    }

    for b in bodies:
        if b.name in rot_map:
            b.rotation_speed = rot_map[b.name]


def draw_scene():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    
    
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60, WINDOW_WIDTH/WINDOW_HEIGHT, 0.1, 5000)
    
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    
    
    camera.update_physics()
    gluLookAt(*camera.get_view_matrix())
    
    
    starfield.draw()
    asteroid_belt.draw()
    
    # Draw Bodies
    for i, b in enumerate(bodies):
        b.draw(i == selected_index)
        
    
    for b in bodies:
        if b.name == "Saturn":
            
            draw_ring_system(b.size * 1.4, b.size * 2.2, b.position, b.axial_tilt, 0)

    
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    
    # 1. Main Stats HUD (Top Left)
    draw_hud_text(20, WINDOW_HEIGHT - 30, "SOLAR SYSTEM SIMULATOR PRO", FONT_HEADER)
    draw_hud_text(20, WINDOW_HEIGHT - 60, f"Speed: {sim_speed:.1f}x (Press +/-)", FONT_BODY)
    draw_hud_text(20, WINDOW_HEIGHT - 80, f"Status: {'PAUSED' if is_paused else 'RUNNING'}", FONT_BODY)
    draw_hud_text(20, WINDOW_HEIGHT - 100, f"Cam Pos: {camera.position}", FONT_BODY)
    
    # 2. Controls Help (Top Right)
    help_x = WINDOW_WIDTH - 250
    draw_hud_text(help_x, WINDOW_HEIGHT - 30, "CONTROLS", FONT_HEADER)
    draw_hud_text(help_x, WINDOW_HEIGHT - 60, "WASD: Move Camera", FONT_BODY)
    draw_hud_text(help_x, WINDOW_HEIGHT - 80, "Arrows: Rotate View", FONT_BODY)
    draw_hud_text(help_x, WINDOW_HEIGHT - 100, "Q/E: Lift/Lower", FONT_BODY)
    draw_hud_text(help_x, WINDOW_HEIGHT - 120, "R/F: Orbit Vertical", FONT_BODY)
    draw_hud_text(help_x, WINDOW_HEIGHT - 140, "Click: Select Planet", FONT_BODY)

    # 3. Selected Planet Info (Bottom Left)
    if selected_index != -1:
        sel = bodies[selected_index]
        draw_hud_text(20, 250, f"SELECTED: {sel.name.upper()}", FONT_HEADER, COLOR_YELLOW)
        draw_hud_text(20, 220, f"Type: {sel.type_str}", FONT_BODY)
        draw_hud_text(20, 200, f"Radius: {sel.size} km (scale)", FONT_BODY)
        draw_hud_text(20, 180, f"Orbit: {sel.orbit_radius} AU (scale)", FONT_BODY)
        draw_hud_text(20, 160, f"X: {sel.position.x:.1f} Y: {sel.position.y:.1f}", FONT_BODY)
        
    
    console.draw()
    glutSwapBuffers()


def update_loop():
    global is_paused, sim_speed
    
    if not is_paused:
       
        for b in bodies:
            b.update(sim_speed)
        
       
        asteroid_belt.update(sim_speed)
        
    glutPostRedisplay()


# ==============================================================================
#   SECTION 8: INPUT HANDLERS
# ==============================================================================

def keyboard_handler(key, x, y):
    global sim_speed, is_paused, console
    
    step = 5.0
    
    if key == b'w':   camera.move_forward()
    elif key == b's': camera.move_backward()
    elif key == b'a': camera.move_left()
    elif key == b'd': camera.move_right()
    elif key == b'q': camera.move_up()
    elif key == b'e': camera.move_down()
    
    # Reference Orbiting
    elif key == b'r': camera.orbit_vertical(2.0)
    elif key == b'f': camera.orbit_vertical(-2.0)
    
   
    elif key == b'z': camera.roll(2.0)
    elif key == b'c': camera.roll(-2.0)
    
    
    elif key == b' ': 
        is_paused = not is_paused
        console.add_message("Simulation Paused" if is_paused else "Simulation Resumed")
    elif key == b'+' or key == b'=': 
        sim_speed += 0.1
        console.add_message(f"Speed Increased: {sim_speed:.1f}")
    elif key == b'-': 
        sim_speed = max(0, sim_speed - 0.1)
        console.add_message(f"Speed Decreased: {sim_speed:.1f}")
    elif key == b'\x1b': 
        glutLeaveMainLoop()

def special_key_handler(key, x, y):
    if key == GLUT_KEY_LEFT:  camera.look_yaw(2.0)
    elif key == GLUT_KEY_RIGHT: camera.look_yaw(-2.0)
    elif key == GLUT_KEY_UP:    camera.look_pitch(2.0)
    elif key == GLUT_KEY_DOWN:  camera.look_pitch(-2.0)

def mouse_handler(button, state, x, y):
    global selected_index, console
    if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
       
        selected_index += 1
        if selected_index >= len(bodies):
            selected_index = -1
            console.add_message("Selection Cleared")
        else:
            name = bodies[selected_index].name
            console.add_message(f"Selected: {name}")

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT)
    glutCreateWindow(WINDOW_TITLE)
    
    glEnable(GL_DEPTH_TEST)
    glClearColor(0.05, 0.05, 0.1, 1.0) 
    
    init_world()
    
    glutDisplayFunc(draw_scene)
    glutIdleFunc(update_loop)
    glutKeyboardFunc(keyboard_handler)
    glutSpecialFunc(special_key_handler)
    glutMouseFunc(mouse_handler)
    
    print("Starting Solar System Procedural Edition...")
    glutMainLoop()

if __name__ == "__main__":
    main()