import pygame
import pygame_gui
import random
import time
from mesa import Agent as MesaAgent, Model as MesaModel
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector

class Message:
    def __init__(self, sender, receiver, content):
        self.sender = sender
        self.receiver = receiver
        self.content = content

class Agent:
    def __init__(self, unique_id, model, role):
        self.unique_id = unique_id
        self.model = model
        self.role = role
        self.status = "active"
        self.pos = (random.randint(0, model.grid_width - 1), random.randint(0, model.grid_height - 1))
        self.messages = []
        
        # Role-specific attributes
        if role == "citizen":
            self.trust_level = random.randint(0, 100)
            self.icon = model.citizen_icon
        elif role == "dealer":
            self.icon = model.dealer_icon
        elif role == "police":
            self.icon = model.police_icon
        elif role == "data-collector":
            self.icon = model.data_collector_icon
        elif role == "drug-user":
            self.icon = model.drug_user_icon
    
    def move_nearby(self):
        # Move to a nearby grid cell instead of completely random
        x, y = self.pos
        dx = random.randint(-1, 1)
        dy = random.randint(-1, 1)
        new_x = max(0, min(self.model.grid_width - 1, x + dx))
        new_y = max(0, min(self.model.grid_height - 1, y + dy))
        self.pos = (new_x, new_y)
    
    def step(self):
        if self.status == "active":
            self.move_nearby()
            
            if self.role == "citizen":
                self.citizen_behavior()
            elif self.role == "dealer":
                self.dealer_behavior()
            elif self.role == "police":
                self.police_behavior()
            elif self.role == "data-collector":
                self.data_collector_behavior()
    
    def citizen_behavior(self):
        # More nuanced drug user conversion
        nearby_dealers = sum(1 for agent in self.model.agents 
                            if agent.role == "dealer" and agent.status == "active" 
                            and agent.pos == self.pos)
        
        if nearby_dealers > 0 and random.random() < 0.3:
            # Only some citizens become drug users
            if random.random() < 0.5:  # 50% chance to become a drug user
                self.role = "drug-user"
                self.icon = self.model.drug_user_icon
                self.model.drug_users += 1
    
    def dealer_behavior(self):
        # Dealers avoid police and data collectors
        nearby_police = sum(1 for agent in self.model.agents 
                            if agent.role == "police" and agent.status == "active" 
                            and agent.pos == self.pos)
        nearby_data_collectors = sum(1 for agent in self.model.agents 
                                     if agent.role == "data-collector" and agent.status == "active" 
                                     and agent.pos == self.pos)
        
        if nearby_police > 0 or nearby_data_collectors > 0:
            # Move away from police and data collectors
            self.move_away_from(nearby_police, nearby_data_collectors)
        else:
            # Find a nearby patch with high drug presence
            if random.random() < 0.3:
                possible_moves = [
                    (self.pos[0]+dx, self.pos[1]+dy) 
                    for dx in [-1,0,1] 
                    for dy in [-1,0,1]
                    if 0 <= self.pos[0]+dx < self.model.grid_width and 
                       0 <= self.pos[1]+dy < self.model.grid_height
                ]
                best_move = max(possible_moves, key=lambda p: self.model.drug_presence.get(p, 0))
                self.pos = best_move
    
    def move_away_from(self, nearby_police, nearby_data_collectors):
        # Move to a grid cell away from police and data collectors
        x, y = self.pos
        dx = random.choice([-1, 1])
        dy = random.choice([-1, 1])
        new_x = max(0, min(self.model.grid_width - 1, x + dx))
        new_y = max(0, min(self.model.grid_height - 1, y + dy))
        self.pos = (new_x, new_y)
    
    def police_behavior(self):
        # More targeted arrest logic with intelligence
        nearby_agents = [
            agent for agent in self.model.agents 
            if (agent.role == "drug-user" or agent.role == "dealer") 
            and agent.status == "active" 
            and agent.pos == self.pos
        ]
        
        if nearby_agents and random.random() < 0.4:
            target = random.choice(nearby_agents)
            target.status = "inactive"
            target.icon = self.model.arrest_icon  # Change icon to arrest.png
            self.model.arrests += 1
            
            if target.role == "dealer":
                self.model.drug_dealers -= 1
            elif target.role == "drug-user":
                self.model.drug_users -= 1
    
    def data_collector_behavior(self):
        # More comprehensive data collection
        nearby_agents = [
            agent for agent in self.model.agents 
            if agent.role == "drug-user" and agent.status == "active"
        ]
        
        if nearby_agents:
            if self.pos not in self.model.drug_presence:
                self.model.drug_presence[self.pos] = 0
            self.model.drug_presence[self.pos] += len(nearby_agents)
        
        # Send messages to police and civilians
        for agent in self.model.agents:
            if agent.pos == self.pos:
                if agent.role == "police":
                    self.send_message(agent, "Drug activity detected")
                elif agent.role == "citizen":
                    self.send_message(agent, "Stay safe, drug activity nearby")

    def send_message(self, receiver, content):
        message = Message(self.unique_id, receiver.unique_id, content)
        receiver.receive_message(message)
        self.model.messages.append(message)

    def receive_message(self, message):
        self.messages.append(message)
        print(f"Agent {self.unique_id} received message from Agent {message.sender}: {message.content}")

class DrugModel:
    def __init__(self, width, height, num_citizens, num_dealers, num_police, num_data_collectors):
        self.grid_width = width
        self.grid_height = height
        self.drug_users = 0
        self.drug_dealers = num_dealers
        self.arrests = 0
        self.drug_presence = {}
        self.simulation_time = 0
        self.messages = []  # Store messages
        
        # Load icons
        try:
            self.citizen_icon = pygame.image.load('assets/citizen.png')
            self.dealer_icon = pygame.image.load('assets/dealer.png')
            self.police_icon = pygame.image.load('assets/police.png')
            self.data_collector_icon = pygame.image.load('assets/data_collector.png')
            self.drug_user_icon = pygame.image.load('assets/drug_user.png')
            self.arrest_icon = pygame.image.load('assets/arrest.png')  # Load arrest.png
        except pygame.error as e:
            print(f"Error loading images: {e}")
            pygame.quit()
            exit()

        # Scale icons to fit the grid size
        self.citizen_icon = pygame.transform.scale(self.citizen_icon, (20, 20))
        self.dealer_icon = pygame.transform.scale(self.dealer_icon, (20, 20))
        self.police_icon = pygame.transform.scale(self.police_icon, (20, 20))
        self.data_collector_icon = pygame.transform.scale(self.data_collector_icon, (20, 20))
        self.drug_user_icon = pygame.transform.scale(self.drug_user_icon, (20, 20))
        self.arrest_icon = pygame.transform.scale(self.arrest_icon, (20, 20))  # Scale arrest.png
        
        # Create agents with unified agent creation
        self.agents = []
        
        # Create citizens
        for i in range(num_citizens):
            self.agents.append(Agent(i, self, "citizen"))
        
        # Create dealers
        for i in range(num_dealers):
            self.agents.append(Agent(i + num_citizens, self, "dealer"))
        
        # Create police
        for i in range(num_police):
            self.agents.append(Agent(i + num_citizens + num_dealers, self, "police"))
        
        # Create data collectors
        for i in range(num_data_collectors):
            self.agents.append(Agent(i + num_citizens + num_dealers + num_police, self, "data-collector"))
    
    def step(self):
        if self.drug_dealers > 0:
            for agent in self.agents:
                agent.step()
            self.simulation_time += 1
        else:
            print("Simulation completed: All drug dealers arrested")

def main():
    pygame.init()

    # Enhanced window size
    WINDOW_WIDTH, WINDOW_HEIGHT = 1000,700
    GRID_SIZE = 20
    SIDEBAR_WIDTH = 250

    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Simulation Of Drug Prevension Using Multi Agent System")
    
    # Enhanced UI Manager
    manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT), 
                                   theme_path='assets/themes/default.json')

    # Fonts
    title_font = pygame.font.Font(None, 36)
    label_font = pygame.font.Font(None, 23)
    message_font = pygame.font.Font(None, 15)

    # Simulation parameters
    num_citizens = 200
    num_dealers = 10
    num_police = 10
    num_data_collectors = 5
    model = DrugModel(40, 35, num_citizens, num_dealers, num_police, num_data_collectors)

    # Buttons and Sliders
    setup_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((WINDOW_WIDTH - SIDEBAR_WIDTH + 60, 60), (120, 40)),
        text='Reset Simulation',
        manager=manager
    )

    pause_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((WINDOW_WIDTH - SIDEBAR_WIDTH + 60, 100), (120, 40)),
        text='Pause/Resume',
        manager=manager
    )
    # Agent count sliders
    citizen_slider = pygame_gui.elements.UIHorizontalSlider(
        relative_rect=pygame.Rect((WINDOW_WIDTH - SIDEBAR_WIDTH + 25, 150), (200, 30)),
        start_value=num_citizens,
        value_range=(50, 500),
        manager=manager
    )
    dealer_slider = pygame_gui.elements.UIHorizontalSlider(
        relative_rect=pygame.Rect((WINDOW_WIDTH - SIDEBAR_WIDTH + 25, 200), (200, 30)),
        start_value=num_dealers,
        value_range=(5, 50),
        manager=manager
    )
    police_slider = pygame_gui.elements.UIHorizontalSlider(
        relative_rect=pygame.Rect((WINDOW_WIDTH - SIDEBAR_WIDTH + 25, 250), (200, 30)),
        start_value=num_police,
        value_range=(5, 50),
        manager=manager
    )
    data_collector_slider = pygame_gui.elements.UIHorizontalSlider(
        relative_rect=pygame.Rect((WINDOW_WIDTH - SIDEBAR_WIDTH + 25, 300), (200, 30)),
        start_value=num_data_collectors,
        value_range=(1, 20),
        manager=manager
    )

    # Simulation labels
    clock = pygame.time.Clock()
    running = True
    paused = False
    simulation_speed = 1
    while running:
        delta_time = clock.tick(10) / 1000.0  # Slow down the simulation by reducing the frame rate

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            manager.process_events(event)

            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == setup_button:
                    # Reinitialize the model with updated values
                    num_citizens = int(citizen_slider.get_current_value())
                    num_dealers = int(dealer_slider.get_current_value())
                    num_police = int(police_slider.get_current_value())
                    num_data_collectors = int(data_collector_slider.get_current_value())
                    model = DrugModel(40, 35, num_citizens, num_dealers, num_police, num_data_collectors)
                elif event.ui_element == pause_button:
                    paused = not paused

        manager.update(delta_time)

        # Only step the simulation if not paused
        if not paused:
            for _ in range(simulation_speed):
                model.step()

        # Drawing
        screen.fill((240, 240, 240))  # Light gray background

        # Draw simulation grid
        for agent in model.agents:
            x, y = agent.pos
            icon = agent.icon
            rect = pygame.Rect(x * GRID_SIZE, y * GRID_SIZE, GRID_SIZE, GRID_SIZE)
            screen.blit(icon, rect.topleft)
            pygame.draw.rect(screen, (200, 200, 200), rect, 1)  

        # Sidebar background
        sidebar_rect = pygame.Rect(WINDOW_WIDTH - SIDEBAR_WIDTH, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT)
        pygame.draw.rect(screen, (220, 220, 220), sidebar_rect)

        # Simulation statistics
        title = title_font.render("Drug Prevention", True, (0, 0, 0))
        drug_users_text = label_font.render(f"Drug Users: {model.drug_users}", True, (0, 0, 0))
        drug_dealers_text = label_font.render(f"Drug Dealers: {model.drug_dealers}", True, (0, 0, 0))
        arrests_text = label_font.render(f"Arrests: {model.arrests}", True, (0, 0, 0))
        time_text = label_font.render(f"Simulation Time: {model.simulation_time}", True, (0, 0, 0))

        screen.blit(title, (WINDOW_WIDTH - SIDEBAR_WIDTH + 40, 15))
        screen.blit(drug_users_text, (WINDOW_WIDTH - SIDEBAR_WIDTH + 50, 350))
        screen.blit(drug_dealers_text, (WINDOW_WIDTH - SIDEBAR_WIDTH + 50, 370))
        screen.blit(arrests_text, (WINDOW_WIDTH - SIDEBAR_WIDTH + 50, 390))
        screen.blit(time_text, (WINDOW_WIDTH - SIDEBAR_WIDTH + 50, 410))

        # Agent images
        screen.blit(model.citizen_icon, (WINDOW_WIDTH - SIDEBAR_WIDTH + 25, 435))
        screen.blit(model.data_collector_icon, (WINDOW_WIDTH - SIDEBAR_WIDTH + 25, 458))
        screen.blit(model.police_icon, (WINDOW_WIDTH - SIDEBAR_WIDTH + 25, 481))
        screen.blit(model.dealer_icon, (WINDOW_WIDTH - SIDEBAR_WIDTH + 25, 504))
        screen.blit(model.drug_user_icon, (WINDOW_WIDTH - SIDEBAR_WIDTH + 25, 527))
        screen.blit(model.arrest_icon, (WINDOW_WIDTH - SIDEBAR_WIDTH + 25, 550))
        
        # Icon labels
        citizen_label = label_font.render("Citizen Agent", True, (0, 0, 0))
        dealer_label = label_font.render("Dealer", True, (0, 0, 0))
        police_label = label_font.render("Police Agent", True, (0, 0, 0))
        data_collector_label = label_font.render("Data Collector Agent", True, (0, 0, 0))
        drug_user_label = label_font.render("Drug User", True, (0, 0, 0))
        arrested = label_font.render("Arrested", True, (0, 0, 0))
        last_five_messages = label_font.render("Last 5 Messages", True, (0, 0, 0))

        screen.blit(citizen_label, (WINDOW_WIDTH - SIDEBAR_WIDTH + 60, 437))
        screen.blit(data_collector_label, (WINDOW_WIDTH - SIDEBAR_WIDTH + 60, 462))
        screen.blit(police_label, (WINDOW_WIDTH - SIDEBAR_WIDTH + 60, 485))
        screen.blit(drug_user_label, (WINDOW_WIDTH - SIDEBAR_WIDTH + 60, 532))
        screen.blit(dealer_label, (WINDOW_WIDTH - SIDEBAR_WIDTH + 60, 509))
        screen.blit(arrested, (WINDOW_WIDTH - SIDEBAR_WIDTH + 60, 552)) 
        screen.blit(last_five_messages, (WINDOW_WIDTH - SIDEBAR_WIDTH + 60, 580))

        # Draw messages
        message_y = 700
        for message in model.messages[-6:]:  # Show last 5 messages
            message_text = message_font.render(f"From {message.sender} to {message.receiver}: {message.content}", True, (0, 0, 0))
            screen.blit(message_text, (755, message_y))
            message_y -= 20

        # Draw UI elements
        manager.draw_ui(screen)
        
        pygame.display.update()

    pygame.quit()


if __name__ == "__main__":
    main()
