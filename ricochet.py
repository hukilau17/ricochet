# Ricochet Robots game
# Matthew Kroesche

try:
    # Python 3
    from tkinter import *
    try:
        from tkinter.ttk import Button as ttkButton
    except ImportError:
        pass
except ImportError:
    # Python 2
    from Tkinter import *
    try:
        from ttk import Button as ttkButton
    except ImportError:
        pass

import sys
import random
import time


DEFAULT_BOARD_SIZE = (16, 16)
DEFAULT_CELL_SIZE = 40
DEFAULT_DELAY_SECONDS = 30
DEFAULT_DPAD_SIZE = 150

CELLS_PER_SECOND = 16.0

COLORS = ('red', 'yellow', 'green', 'blue')
OBJECTS = ('square', 'circle', 'triangle', 'diamond')

DRAWFUNCS = {}


def drawfunc(f):
    # Decorator for drawing functions
    DRAWFUNCS[f.__name__] = f
    return f



# Drawing helper functions

tagcount = 0

def getwidth(bbox):
    return (bbox[2] - bbox[0]) * 0.125

@drawfunc
def square(canvas, color, bbox):
    return canvas.create_rectangle(bbox, outline=color, width=getwidth(bbox))

@drawfunc
def circle(canvas, color, bbox):
    return canvas.create_oval(bbox, outline=color, width=getwidth(bbox))

@drawfunc
def triangle(canvas, color, bbox):
    x1, y1, x2, y2 = bbox
    return canvas.create_polygon([
        (x1, y2), (x2, y2),
        ((x1+x2)*.5, y1*.85+y2*.15)],
                                 outline=color, width=getwidth(bbox), fill='')

@drawfunc
def diamond(canvas, color, bbox):
    x1, y1, x2, y2 = bbox
    return canvas.create_polygon([
        (x1, (y1+y2)*.5), ((x1+x2)*.5, y1),
        (x2, (y1+y2)*.5), ((x1+x2)*.5, y2)],
                                 outline=color, width=getwidth(bbox), fill='')

@drawfunc
def wild(canvas, color, bbox):
    global tagcount
    tag = 'tag#%d' % tagcount
    tagcount += 1
    x1, y1, x2, y2 = bbox
    ctr = ((x1+x2)*.5, (y1+y2)*.5)
    canvas.create_polygon([(x1, y1), (x2, y1), ctr], fill='red', width=0, tags=tag)
    canvas.create_polygon([(x1, y2), (x2, y2), ctr], fill='yellow', width=0, tags=tag)
    canvas.create_polygon([(x1, y1), (x1, y2), ctr], fill='green', width=0, tags=tag)
    canvas.create_polygon([(x2, y1), (x2, y2), ctr], fill='blue', width=0, tags=tag)
    return tag












# Tk helper functions

def test_ttkbutton():
    # Make sure creating fancy ttk Buttons is supported.
    global ttkButton
    try:
        btn = ttkButton()
    except (NameError, TclError):
        # If not, fall back on the regular Tk implementation
        ttkButton = Button
    else:
        btn.destroy()
        

def enable_button(b, enable):
    # Enabling/disabling works differently depending on if we're using ttk
    if ttkButton == Button:
        b['state'] = (NORMAL if enable else DISABLED)
    else:
        b.state(['!disabled' if enable else 'disabled'])







class Robot(object):

    # Helper class to track the information of an individual robot

    def __init__(self, game, color):
        self.game = game
        self.color = color
        self.pos = self.oldpos = self.curpos = self.origpos = None
        self.robot_id = self.marker_id = None

    def delete_robot(self):
        # Delete the robot itself from the canvas
        if (self.robot_id is not None) and self.game.updates_enabled:
            self.game.canvas.delete(self.robot_id)
            self.robot_id = None

    def delete_marker(self):
        # Delete the robot's original position marker from the canvas
        self.origpos = self.pos
        if (self.marker_id is not None) and self.game.updates_enabled:
            self.game.canvas.delete(self.marker_id)
            self.marker_id = None

    def draw(self, pos=None):
        # Redraw the robot
        if self.game.updates_enabled:
            if pos is None:
                pos = self.pos
            if pos is not None:
                self.delete_robot()
                x, y = [(i+.5)*self.game.cellsize for i in pos]
                r = .4 * self.game.cellsize
                self.robot_id = self.game.canvas.create_oval((x-r, y-r, x+r, y+r), fill=self.color)

    def setpos(self, pos):
        # Set the initial position of the robot
        self.pos = self.oldpos = pos
        self.curpos = list(map(float, self.pos))
        self.delete_marker()
        self.draw()

    def reset(self):
        # Move the robot back to where it started
        self.setpos(self.origpos)

    def move(self, pos):
        # Move the robot from one place to another
        if self.pos is None:
            self.setpos(pos)
        else:
            self.oldpos = self.pos
            if self.curpos is None:
                self.curpos = list(map(float, self.pos))
            self.pos = pos
            self.game.moves.append((self, self.oldpos, self.pos))
            if self.game.updates_enabled:
                self.game.begin_moving(self)
                if self.marker_id is None:
                    x, y = [(i+.5)*self.game.cellsize for i in self.origpos]
                    r = .4 * self.game.cellsize
                    self.marker_id = self.game.canvas.create_oval((x-r, y-r, x+r, y+r), outline=self.color)





class Target(object):

    def __init__(self, game, color, draw):
        self.game = game
        self.color = color
        self.draw = draw # draw() should take a canvas, color, and bbox argument
        # and return a tag or id
        self.pos = None
        self.id = None

    def delete(self):
        # Delete the target from the canvas
        if self.id is not None:
            self.game.canvas.delete(self.id)
            self.id = None

    def setpos(self, pos):
        # Set the position of the target
        self.pos = x, y = pos
        self.delete()
        cs = self.game.cellsize
        self.id = self.draw(self.game.canvas, self.color,
                            ((x+.3)*cs, (y+.3)*cs,
                             (x+.7)*cs, (y+.7)*cs))

    def make_goal(self):
        # Set this target to the goal
        self.game.delete_goal()
        cs = self.game.cellsize
        cx = self.game.size[0] * cs // 2
        cy = self.game.size[1] * cs // 2
        id = self.draw(self.game.canvas, self.color, (cx-.7*cs, cy-.7*cs, cx+.7*cs, cy+.7*cs))
        self.game.canvas.tag_raise(id)
        self.game.goal_id = id





class Wall(object):

    def __init__(self, game, pos):
        self.game = game
        self.pos = pos
        self.id = None
        self.create()

    def delete(self):
        # Delete the wall object
        if self.id is not None:
            self.game.canvas.delete(self.id)
            self.id = None

    def create(self):
        # Draw the wall object. Called automatically at initialization.
        self.delete()
        s = self.game.cellsize // 2
        x, y = self.pos
        if x % 2:
            bbox = ((x+.9)*s, (y-.1)*s, (x+1.1)*s, (y+2.1)*s)
        else:
            bbox = ((x-.1)*s, (y+.9)*s, (x+2.1)*s, (y+1.1)*s)
        self.id = self.game.canvas.create_rectangle(bbox, fill='gray20', width=0)
        self.game.canvas.tag_raise(self.id)
        











class Game(Tk):

    # Constructor

    def __init__(self, size=DEFAULT_BOARD_SIZE, cellsize=DEFAULT_CELL_SIZE,
                 delay=DEFAULT_DELAY_SECONDS, dpadsize=DEFAULT_DPAD_SIZE,
                 colors=COLORS, objects=OBJECTS, **drawfuncs):
        Tk.__init__(self)
        self.size = size
        self.cellsize = cellsize
        self.delay = delay
        self.dpadsize = dpadsize
        self.colors = colors
        self.objects = objects
        self.drawfuncs = DRAWFUNCS.copy()
        self.drawfuncs.update(drawfuncs)
        self.title('Ricochet Robots')
        self.moving = []
        self.updates_enabled = True
        self.buttons_enabled = True
        self.create_canvas()
        self.create_controls()
        self.reset_game()




    # Methods to initialize various parts of the game


    def create_canvas(self):
        if hasattr(self, 'canvas'):
            self.canvas.destroy()
        # Initialize canvas
        w, h = self.size
        self.canvas = Canvas(self, width = w * self.cellsize, height = h * self.cellsize)
        self.canvas.pack(side=LEFT)
        # Place cells in grid frame
        for i in range(w):
            for j in range(h):
                if (w//2 in (i, i+1)) and (h//2 in (j, j+1)):
                    continue # Leave cell as None since the middle block is going to go there
                self.canvas.create_rectangle(
                    (i*self.cellsize, j*self.cellsize, (i+1)*self.cellsize, (j+1)*self.cellsize),
                    fill='gray50')
                self.canvas.create_oval(
                    ((i+.1)*self.cellsize, (j+.1)*self.cellsize, (i+.9)*self.cellsize, (j+.9)*self.cellsize),
                    fill='gray80', width=0)
        # Create center block
        self.canvas.create_rectangle(
            ((w//2-1)*self.cellsize, (h//2-1)*self.cellsize, (w//2+1)*self.cellsize, (h//2+1)*self.cellsize),
            fill='gray20')
        self.center_positions = [(x, y) for x in (w//2-1, w//2) for y in (h//2-1, h//2)]
        # Create robots
        self.robots = {}
        for color in self.colors:
            self.robots[color] = Robot(self, color)
        # Create targets
        self.targets = {}
        self.goal = None
        self.goal_id = None
        for color in self.colors:
            for object in self.objects:
                self.targets[color, object] = Target(self, color, self.drawfuncs[object])
        self.targets['wild', 'wild'] = Target(self, 'wild', self.drawfuncs['wild'])
        # Create the edge walls
        self.walls = []
        W = [int(round(i * self.size[0] / 4.0)) for i in range(5)]
        H = [int(round(j * self.size[1] / 4.0)) for j in range(5)]
        self.walls.append(Wall(self, (2*W[0]  , 2*H[1]-1)))
        self.walls.append(Wall(self, (2*W[0]  , 2*H[3]-1)))
        self.walls.append(Wall(self, (2*W[4]-2, 2*H[1]-1)))
        self.walls.append(Wall(self, (2*W[4]-2, 2*H[3]-1)))
        self.walls.append(Wall(self, (2*W[1]-1, 2*H[0]  )))
        self.walls.append(Wall(self, (2*W[3]-1, 2*H[0]  )))
        self.walls.append(Wall(self, (2*W[1]-1, 2*H[4]-2)))
        self.walls.append(Wall(self, (2*W[3]-1, 2*H[4]-2)))
        
        


    def create_dpad(self, color):
        dpad = Frame(self.control_frame, width=self.dpadsize, height=self.dpadsize,
                     takefocus=True, highlightthickness=1, highlightcolor='cyan')
        dpad.color = color
        # Create directional buttons
        dpad.up    = Label(dpad, background=color, borderwidth=1, relief=SOLID)
        dpad.down  = Label(dpad, background=color, borderwidth=1, relief=SOLID)
        dpad.left  = Label(dpad, background=color, borderwidth=1, relief=SOLID)
        dpad.right = Label(dpad, background=color, borderwidth=1, relief=SOLID)
        # Bind commands to directional buttons
        dpad.up   .bind('<ButtonRelease-1>', lambda e: self.buttons_enabled and self.move(color, 'up'   ))
        dpad.down .bind('<ButtonRelease-1>', lambda e: self.buttons_enabled and self.move(color, 'down' ))
        dpad.left .bind('<ButtonRelease-1>', lambda e: self.buttons_enabled and self.move(color, 'left' ))
        dpad.right.bind('<ButtonRelease-1>', lambda e: self.buttons_enabled and self.move(color, 'right'))
        # Bind focus removal to these buttons as well
        dpad.up   .bind('<ButtonRelease-1>', lambda e: self.buttons_enabled and self.focus_set(), '+')
        dpad.down .bind('<ButtonRelease-1>', lambda e: self.buttons_enabled and self.focus_set(), '+')
        dpad.left .bind('<ButtonRelease-1>', lambda e: self.buttons_enabled and self.focus_set(), '+')
        dpad.right.bind('<ButtonRelease-1>', lambda e: self.buttons_enabled and self.focus_set(), '+')
        # Position directional buttons
        dpad.up   .place(relx=0.5 , rely=0.25, relwidth=0.1, relheight=0.3, anchor=CENTER)
        dpad.down .place(relx=0.5 , rely=0.75, relwidth=0.1, relheight=0.3, anchor=CENTER)
        dpad.left .place(relx=0.25, rely=0.5 , relwidth=0.3, relheight=0.1, anchor=CENTER)
        dpad.right.place(relx=0.75, rely=0.5 , relwidth=0.3, relheight=0.1, anchor=CENTER)
        return dpad



    def create_controls(self):
        # Initialize control frame
        self.control_frame = Frame()
        self.control_frame.pack(side=LEFT, expand=YES, fill=BOTH)
        # Create robot control pads
        self.dpads = []
        for i, color in enumerate(self.colors):
            dpad = self.create_dpad(color)
            dpad.grid(row=i//2, column=3*(i%2), columnspan=3)
            self.dpads.append(dpad)
        row = (len(self.colors)+1)//2
        # Create control buttons
        self.control_frame.grid_rowconfigure(row, minsize=30) # Add a spacer
        row += 1
        test_ttkbutton()
        self.draw_button = ttkButton(self.control_frame, text='Draw', command=self.draw)
        self.draw_button.grid(row=row, column=0, padx=10, pady=10, sticky=E+W)
        self.time_button = ttkButton(self.control_frame, text='Timer', command=self.time)
        self.time_button.grid(row=row, column=1, padx=10, pady=10, sticky=E+W)
        self.undo_button = ttkButton(self.control_frame, text='Undo', command=self.undo)
        self.undo_button.grid(row=row, column=2, padx=10, pady=10, sticky=E+W)
        self.redo_button = ttkButton(self.control_frame, text='Redo', command=self.redo)
        self.redo_button.grid(row=row, column=3, padx=10, pady=10, sticky=E+W)
        self.reset_button = ttkButton(self.control_frame, text='Reset', command=self.reset_robots)
        self.reset_button.grid(row=row, column=4, padx=10, pady=10, sticky=E+W)
        # Create move counter
        self.move_label = Label(self.control_frame)
        row += 1
        self.move_label.grid(row=row, column=0, columnspan=6, sticky=E+W)
        # Create timer display
        row += 1
        self.control_frame.grid_rowconfigure(row, minsize=30) # Add a spacer
        row += 1
        self.timer_frame = Frame(self.control_frame)
        self.timer_frame.grid(row=row, column=0, columnspan=6, sticky=N+S+E+W, padx=10, pady=10)
        self.seconds_label = Label(self.timer_frame, font=('TkDefaultFont', 50))
        self.seconds_label.pack(side=LEFT, anchor=N+W)
        self.hundredths_label = Label(self.timer_frame, font=('TkDefaultFont', 12))
        self.hundredths_label.pack(side=LEFT, anchor=N+W)
        # Create new game button
        row += 1
        self.control_frame.grid_rowconfigure(row, minsize=30, weight=1) # Stretchable spacer
        row += 1
        self.new_button = ttkButton(self.control_frame, text='Start new game', command=self.reset_game)
        self.new_button.grid(row=row, column=0, columnspan=6, sticky=E+W, padx=10, pady=10)
        # Create undo/redo shortcuts
        if sys.platform == 'darwin':
            self.bind('<Command-d>'      , lambda e: self.buttons_enabled and self.draw        ())
            self.bind('<Command-t>'      , lambda e: self.buttons_enabled and self.time        ())
            self.bind('<Command-r>'      , lambda e: self.buttons_enabled and self.reset_robots())
            self.bind('<Command-z>'      , lambda e: self.buttons_enabled and self.undo        ())
            self.bind('<Command-Shift-z>', lambda e: self.buttons_enabled and self.redo        ())
            self.bind('<Command-y>'      , lambda e: self.buttons_enabled and self.redo        ())
        else:
            self.bind('<Control-d>'      , lambda e: self.buttons_enabled and self.draw        ())
            self.bind('<Control-t>'      , lambda e: self.buttons_enabled and self.time        ())
            self.bind('<Control-r>'      , lambda e: self.buttons_enabled and self.reset_robots())
            self.bind('<Control-z>'      , lambda e: self.buttons_enabled and self.undo        ())
            self.bind('<Control-Shift-z>', lambda e: self.buttons_enabled and self.redo        ())
            self.bind('<Control-y>'      , lambda e: self.buttons_enabled and self.redo        ())
        # Create arrow shortcuts
        def func(i):
            return lambda e: self.dpads[i].focus_set()
        for i, color in enumerate(self.colors):
            self.bind(color[0], func(i))
        self.bind('<Up>'   , lambda e: self.buttons_enabled and self.dpad_move_shortcut('up'   ))
        self.bind('<Down>' , lambda e: self.buttons_enabled and self.dpad_move_shortcut('down' ))
        self.bind('<Left>' , lambda e: self.buttons_enabled and self.dpad_move_shortcut('left' ))
        self.bind('<Right>', lambda e: self.buttons_enabled and self.dpad_move_shortcut('right'))



    def dpad_move_shortcut(self, direction):
        dpad = self.focus_get()
        if dpad and dpad in self.dpads:
            self.move(dpad.color, direction)





    # Callback methods


    def is_at_goal(self):
        # True if the current goal is met, False if not
        if not self.goal:
            return False
        if self.goal.color == 'wild':
            return any([robot.pos == self.goal.pos for robot in self.robots.values()])
        return self.robots[self.goal.color].pos == self.goal.pos


    def update_moves(self, index):
        # Update the move index in the stack.
        self.move_index = index
        self.start_time = None # Cancel the timer if somebody moved
        if self.updates_enabled:
            # Update the label accordingly
            if self.move_index == 0:
                self.move_label['text'] = ''
            elif self.move_index == 1:
                self.move_label['text'] = '1 move'
            else:
                self.move_label['text'] = '%d moves' % self.move_index
            # Update the color of the label depending on if we're in the right place
            if self.is_at_goal():
                self.move_label['foreground'] = 'green'    
            else:
                self.move_label['foreground'] = 'black'
            # Update whether the undo/redo buttons are active
            enable_button(self.undo_button, self.move_index > 0)
            enable_button(self.redo_button, self.move_index < len(self.moves))


    def reset_moves(self):
        # Resets the move stack
        self.moves = []
        self.update_moves(0)
        self.focus_set()
        for robot in self.robots.values():
            robot.delete_marker()


    def reset_robots(self):
        # Reset the position of the robots since the last object was drawn.
        # This doesn't clear the stack, but rather moves back to the beginning of it.
        # It's functionally equivalent to hitting "undo" as many times as you can.
        self.update_moves(0)
        self.moving = []
        for robot in self.robots.values():
            robot.reset()


    def delete_goal(self):
        # Delete the goal item from the canvas
        if self.goal_id is not None:
            self.canvas.delete(self.goal_id)
            self.goal_id = None
            

    def reset_game(self):
        # Start a new game. Randomize the game board,
        # clear the stack, and fill the bag back up.
        self.randomize()
        self.reset_moves()
        enable_button(self.draw_button, True)
        self.bag = list(self.targets)
        self.delete_goal()


    def draw(self):
        # Draw a new object out of the bag. This removes all the markers and
        # clears the stack.
        if self.bag:
            self.reset_moves()
            key = random.choice(self.bag)
            self.bag.remove(key)
            if not self.bag:
                enable_button(self.draw_button, False)
            self.goal = self.targets[key]
            self.targets[key].make_goal()


    def time(self):
        # Toggles the timer, either starts it or clears it.
        if self.start_time is None:
            self.start_time = time.time()
        else:
            self.start_time = None


    def begin_moving(self, robot):
        # Start moving the indicated robot
        if self.updates_enabled:
            self.moving.append((robot, robot.pos))


    def move(self, color, direction):
        # Moves the robot given by "color" in the direction given by "direction".
        # Return True if the robot actually moved
        robot = self.robots[color]
        x, y = robot.pos
        # Determine the new value of robot.pos. Robots keep moving until they hit
        # a wall or another robot.
        while True:
            if direction == 'up':
                x2, y2 = x, y-1
            elif direction == 'down':
                x2, y2 = x, y+1
            elif direction == 'left':
                x2, y2 = x-1, y
            elif direction == 'right':
                x2, y2 = x+1, y
            if not ((0 <= x2 < self.size[0]) and (0 <= y2 < self.size[0])):
                break # We hit the edge of the board
            if any([other.pos == (x2, y2) for other in self.robots.values()]):
                break # We hit another robot
            if any([wall.pos == (x+x2, y+y2) for wall in self.walls]):
                break # We hit a wall
            if (x2, y2) in self.center_positions:
                break # We hit the thing in the center of the board
            # We didn't hit anything, update the position and repeat
            x, y = x2, y2
        moved = ((x, y) != robot.pos)
        # Update the stack
        del self.moves[self.move_index:]
        robot.move((x, y))
        self.update_moves(self.move_index + 1)
        return moved


    def undo(self):
        # Undo the most recent action if possible
        if self.moves and (self.move_index != 0):
            robot, start, end = self.moves[self.move_index - 1]
            robot.pos = start
            self.begin_moving(robot)
            self.update_moves(self.move_index - 1)


    def redo(self):
        # Redo the most recent action if possible
        if self.moves and (self.move_index < len(self.moves)):
            robot, start, end = self.moves[self.move_index]
            robot.pos = end
            self.begin_moving(robot)
            self.update_moves(self.move_index + 1)


        


    # Function to randomly position everything

    def randomize(self):
        # Delete any preexisting walls
        for wall in self.walls[8:]:
            wall.delete()
        del self.walls[8:]
        # Get the list of objects we need to randomly place
        objects = list(self.robots.values()) + list(self.targets.values())
        # Figure out if we can afford to get rid of the edges
        if (self.size[0] - 1) * (self.size[1] - 1) - 4 >= 5 * len(objects):
            points = [(x, y) for x in range(1, self.size[0]-1) for y in range(1, self.size[1]-1)]
        else:
            points = [(x, y) for x in range(self.size[0]) for y in range(self.size[1])]
        for point in self.center_positions:
            points.remove(point)
        # Figure out if we can afford to avoid placing targets diagonally next to one another
        diag = (len(points) >= 9 * len(objects))
        for object in objects:
            # Randomly choose as many points as we need
            point = random.choice(points)
            # Avoid having a point next to another point if possible
            if diag:
                points = [(x, y) for x, y in points if max([abs(x-point[0]), abs(y-point[1])]) > 1]
            else:
                points = [(x, y) for x, y in points if sum([abs(x-point[0]), abs(y-point[1])]) > 1]
            # Place the target at that point
            object.setpos(point)
            if object not in self.robots.values():
                # It's a target, create the walls to go with the target
                # and put them on random sides
                self.walls.append(Wall(self, (2*point[0] + random.choice([-1, 1]), 2*point[1]                         )))
                self.walls.append(Wall(self, (2*point[0]                         , 2*point[1] + random.choice([-1, 1]))))
        
        
                
                   

    # Main game loop

    def run(self):
        try:
            while True:
                last_update = time.time()
                # Update Tk event loop
                self.update()
                # Update the timer
                if self.start_time is None:
                    if self.seconds_label['text']:
                       self.seconds_label['text'] = self.hundredths_label['text'] = ''
                else:
                    diff = self.delay - (time.time() - self.start_time)
                    if diff < 0:
                        self.seconds_label['text'] = '0'
                        self.hundredths_label['text'] = '00'
                    else:
                        self.seconds_label['text'] = str(int(diff))
                        self.hundredths_label['text'] = '%.2d' % (int(diff * 100) % 100)
                # Update the moving objects
                if self.moving and self.updates_enabled:
                    robot, pos = self.moving[0]
                    # Determine the max distance we can move
                    dt = (time.time() - last_update)
                    d = CELLS_PER_SECOND * dt
                    # Moving in x and y directions
                    delta = []
                    for i in range(2):
                        if abs(pos[i] - robot.curpos[i]) <= d:
                            robot.curpos[i] = float(pos[i])
                            delta.append((pos[i] - robot.curpos[i]) * self.cellsize)
                        elif robot.curpos[i] < pos[i]:
                            robot.curpos[i] += d
                            delta.append(d * self.cellsize)
                        else:
                            robot.curpos[i] -= d
                            delta.append(-d * self.cellsize)
                    self.canvas.move(robot.robot_id, *delta)
                    if robot.curpos == list(pos):
                        if robot.pos == robot.origpos == list(pos):
                            robot.delete_marker()
                        robot.draw(pos)
                        del self.moving[0]
        except TclError:
            try:
                self.destroy()
            except TclError:
                pass
            sys.exit()
            
        
            
            
        
        
            
        
# Run the application

if __name__ == '__main__':
    game = Game()
    game.run()
        
                
