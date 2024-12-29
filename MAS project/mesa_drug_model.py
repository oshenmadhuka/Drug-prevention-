import pygame
import pygame_gui
import random
import time
from mesa import Agent as MesaAgent, Model as MesaModel
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector

class Agent:
    def __init__(self, unique_id, model, role):
        self.unique_id = unique_id
        self.model = model
        self.role = role
        self.status = "active"
        self.pos = (random.randint(0, model.grid_width - 1), random.randint(0, model.grid_height - 1))
        
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
        # Dealers tend to stay in areas with high drug presence
        if random.random() < 0.3:
            # Find a nearby patch with high drug presence
            possible_moves = [
                (self.pos[0]+dx, self.pos[1]+dy) 
                for dx in [-1,0,1] 
                for dy in [-1,0,1]
                if 0 <= self.pos[0]+dx < self.model.grid_width and 
                   0 <= self.pos[1]+dy < self.model.grid_height
            ]
            best_move = max(possible_moves, key=lambda p: self.model.drug_presence.get(p, 0))
            self.pos = best_move
    
    def police_behavior(self):
        # More targeted arrest logic
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

class DrugModel:
    def __init__(self, width, height, num_citizens, num_dealers, num_police, num_data_collectors):
        self.grid_width = width
        self.grid_height = height
        self.drug_users = 0
        self.drug_dealers = num_dealers
        self.arrests = 0
        self.drug_presence = {}
        self.simulation_time = 0
        
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
    pygame.display.set_caption("Drug Market Simulation")
    
    # Enhanced UI Manager
    manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT), 
                                   theme_path='assets/themes/default.json')

    # Fonts
    title_font = pygame.font.Font(None, 36)
    label_font = pygame.font.Font(None, 24)

    # Simulation parameters
    num_citizens = 200
    num_dealers = 10
    num_police = 10
    num_data_collectors = 5
    model = DrugModel(40, 35, num_citizens, num_dealers, num_police, num_data_collectors)

    # Buttons and Sliders
    setup_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((WINDOW_WIDTH - SIDEBAR_WIDTH + 25, 50), (150, 40)),
        text='Reset Simulation',
        manager=manager
    )

    pause_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((WINDOW_WIDTH - SIDEBAR_WIDTH + 25, 120), (150, 40)),
        text='Pause/Resume',
        manager=manager
    )
    # Agent count sliders
    citizen_slider = pygame_gui.elements.UIHorizontalSlider(
        relative_rect=pygame.Rect((WINDOW_WIDTH - SIDEBAR_WIDTH + 25, 200), (200, 30)),
        start_value=num_citizens,
        value_range=(50, 500),
        manager=manager
    )
    dealer_slider = pygame_gui.elements.UIHorizontalSlider(
        relative_rect=pygame.Rect((WINDOW_WIDTH - SIDEBAR_WIDTH + 25, 250), (200, 30)),
        start_value=num_dealers,
        value_range=(5, 50),
        manager=manager
    )
    police_slider = pygame_gui.elements.UIHorizontalSlider(
        relative_rect=pygame.Rect((WINDOW_WIDTH - SIDEBAR_WIDTH + 25, 300), (200, 30)),
        start_value=num_police,
        value_range=(5, 50),
        manager=manager
    )
    data_collector_slider = pygame_gui.elements.UIHorizontalSlider(
        relative_rect=pygame.Rect((WINDOW_WIDTH - SIDEBAR_WIDTH + 25, 350), (200, 30)),
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

            # if event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
            #     if event.ui_element == speed_slider:
            #         simulation_speed = int(event.value)

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
            pygame.draw.rect(screen, (200, 200, 200), rect, 1)  # Grid lines

        # Sidebar background
        sidebar_rect = pygame.Rect(WINDOW_WIDTH - SIDEBAR_WIDTH, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT)
        pygame.draw.rect(screen, (220, 220, 220), sidebar_rect)

        # Simulation statistics
        title = title_font.render("Drug Market Sim", True, (0, 0, 0))
        drug_users_text = label_font.render(f"Drug Users: {model.drug_users}", True, (0, 0, 0))
        drug_dealers_text = label_font.render(f"Drug Dealers: {model.drug_dealers}", True, (0, 0, 0))
        arrests_text = label_font.render(f"Arrests: {model.arrests}", True, (0, 0, 0))
        time_text = label_font.render(f"Simulation Time: {model.simulation_time}", True, (0, 0, 0))

        screen.blit(title, (WINDOW_WIDTH - SIDEBAR_WIDTH + 50, 10))
        screen.blit(drug_users_text, (WINDOW_WIDTH - SIDEBAR_WIDTH + 25, 450))
        screen.blit(drug_dealers_text, (WINDOW_WIDTH - SIDEBAR_WIDTH + 25, 490))
        screen.blit(arrests_text, (WINDOW_WIDTH - SIDEBAR_WIDTH + 25, 530))
        screen.blit(time_text, (WINDOW_WIDTH - SIDEBAR_WIDTH + 25, 570))

        # Agent images
        screen.blit(model.citizen_icon, (WINDOW_WIDTH - SIDEBAR_WIDTH + 25, 610))
        screen.blit(model.dealer_icon, (WINDOW_WIDTH - SIDEBAR_WIDTH + 25, 640))
        screen.blit(model.police_icon, (WINDOW_WIDTH - SIDEBAR_WIDTH + 25, 670))
        screen.blit(model.data_collector_icon, (WINDOW_WIDTH - SIDEBAR_WIDTH + 25, 700))
        screen.blit(model.drug_user_icon, (WINDOW_WIDTH - SIDEBAR_WIDTH + 25, 730))
        # Icon labels
        citizen_label = label_font.render("Citizen", True, (0, 0, 0))
        dealer_label = label_font.render("Dealer", True, (0, 0, 0))
        police_label = label_font.render("Police", True, (0, 0, 0))
        data_collector_label = label_font.render("Data Collector", True, (0, 0, 0))
        drug_user_label = label_font.render("Drug User", True, (0, 0, 0))

        screen.blit(citizen_label, (WINDOW_WIDTH - SIDEBAR_WIDTH + 60, 610))
        screen.blit(dealer_label, (WINDOW_WIDTH - SIDEBAR_WIDTH + 60, 640))
        screen.blit(police_label, (WINDOW_WIDTH - SIDEBAR_WIDTH + 60, 670))
        screen.blit(data_collector_label, (WINDOW_WIDTH - SIDEBAR_WIDTH + 60, 700))
        screen.blit(drug_user_label, (WINDOW_WIDTH - SIDEBAR_WIDTH + 60, 730))

        # Draw UI elements
        manager.draw_ui(screen)
        
        pygame.display.update()

    pygame.quit()


if __name__ == "__main__":
    main()
    class MesaAgentWrapper(MesaAgent):
        def __init__(self, unique_id, model, role):
            super().__init__(unique_id, model)
            self.role = role
            self.status = "active"
            self.pos = (random.randint(0, model.grid_width - 1), random.randint(0, model.grid_height - 1))
            
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

        def move_nearby(self):
            x, y = self.pos
            dx = random.randint(-1, 1)
            dy = random.randint(-1, 1)
            new_x = max(0, min(self.model.grid_width - 1, x + dx))
            new_y = max(0, min(self.model.grid_height - 1, y + dy))
            self.pos = (new_x, new_y)
            self.model.grid.move_agent(self, self.pos)

        def citizen_behavior(self):
            nearby_dealers = sum(1 for agent in self.model.grid.get_neighbors(self.pos, moore=True, include_center=False)
                                if agent.role == "dealer" and agent.status == "active")
            
            if nearby_dealers > 0 and random.random() < 0.3:
                if random.random() < 0.5:
                    self.role = "drug-user"
                    self.icon = self.model.drug_user_icon
                    self.model.drug_users += 1

        def dealer_behavior(self):
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
                self.model.grid.move_agent(self, self.pos)

        def police_behavior(self):
            nearby_agents = [
                agent for agent in self.model.grid.get_neighbors(self.pos, moore=True, include_center=False)
                if (agent.role == "drug-user" or agent.role == "dealer") 
                and agent.status == "active"
            ]
            
            if nearby_agents and random.random() < 0.4:
                target = random.choice(nearby_agents)
                target.status = "inactive"
                target.icon = self.model.arrest_icon
                self.model.arrests += 1
                
                if target.role == "dealer":
                    self.model.drug_dealers -= 1
                elif target.role == "drug-user":
                    self.model.drug_users -= 1

        def data_collector_behavior(self):
            nearby_agents = [
                agent for agent in self.model.grid.get_neighbors(self.pos, moore=True, include_center=False)
                if agent.role == "drug-user" and agent.status == "active"
            ]
            
            if nearby_agents:
                if self.pos not in self.model.drug_presence:
                    self.model.drug_presence[self.pos] = 0
                self.model.drug_presence[self.pos] += len(nearby_agents)

    