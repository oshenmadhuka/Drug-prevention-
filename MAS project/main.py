from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector
from mesa.visualization.modules import CanvasGrid
from mesa.visualization.ModularVisualization import ModularServer
import random

class DrugAgent(Agent):
    """An agent representing a citizen, dealer, police, or data collector."""
    
    def __init__(self, unique_id, model, role):
        super().__init__(unique_id, model)
        self.role = role
        self.trust_level = random.randint(0, 100) if role == "citizen" else None
        self.status = "active"  # active or inactive

    def step(self):
        if self.role == "citizen":
            self.citizen_behavior()
        elif self.role == "dealer":
            self.dealer_behavior()
        elif self.role == "police":
            self.police_behavior()
        elif self.role == "data-collector":
            self.data_collector_behavior()

    def citizen_behavior(self):
        # Move randomly
        new_x = self.pos[0] + random.choice([-1, 0, 1])
        new_y = self.pos[1] + random.choice([-1, 0, 1])
        
        # Check if the new position is within grid bounds
        if (0 <= new_x < self.model.grid.width) and (0 <= new_y < self.model.grid.height):
            self.model.grid.move_agent(self, (new_x, new_y))
            
            # Check for nearby dealers and chance to become a drug user
            nearby_dealers = [agent for agent in self.model.schedule.agents 
                              if agent.role == "dealer" and agent.status == "active"]
            
            if nearby_dealers and random.random() < 0.2:
                # Become a drug user
                self.role = "drug-user"
                self.status = "active"  # Update status if necessary

    def dealer_behavior(self):
        # Move randomly but prefer areas with high drug presence
        new_x = self.pos[0] + random.choice([-1, 0, 1])
        new_y = self.pos[1] + random.choice([-1, 0, 1])
        
        if (0 <= new_x < self.model.grid.width) and (0 <= new_y < self.model.grid.height):
            self.model.grid.move_agent(self, (new_x, new_y))

    def police_behavior(self):
        # Move randomly and try to arrest drug users or dealers
        new_x = self.pos[0] + random.choice([-1, 0, 1])
        new_y = self.pos[1] + random.choice([-1, 0, 1])
        
        if (0 <= new_x < self.model.grid.width) and (0 <= new_y < self.model.grid.height):
            self.model.grid.move_agent(self, (new_x, new_y))
            
            target = [agent for agent in self.model.schedule.agents 
                      if agent.status == "active" and 
                      (agent.role == "drug-user" or agent.role == "dealer")]
            
            if target:
                victim = random.choice(target)
                victim.status = "inactive"
                if victim.role == "dealer":
                    victim.role = "arrested"
                elif victim.role == "drug-user":
                    victim.role = "arrested"

    def data_collector_behavior(self):
        # Move randomly and identify hotspots of drug activity
        new_x = self.pos[0] + random.choice([-1, 0, 1])
        new_y = self.pos[1] + random.choice([-1, 0, 1])
        
        if (0 <= new_x < self.model.grid.width) and (0 <= new_y < self.model.grid.height):
            self.model.grid.move_agent(self, (new_x, new_y))

class DrugModel(Model):
    """A model with some number of agents."""
    
    def __init__(self, N_citizens, N_dealers, N_police, N_data_collectors):
        super().__init__()
        
        self.num_agents = N_citizens + N_dealers + N_police + N_data_collectors
        self.grid = MultiGrid(10, 10, True)  # Change grid size as needed
        self.schedule = RandomActivation(self)

        # Create agents
        for i in range(N_citizens):
            agent = DrugAgent(i, self, "citizen")
            self.schedule.add(agent)
            x = self.random.randrange(self.grid.width)
            y = self.random.randrange(self.grid.height)
            self.grid.place_agent(agent, (x, y))

        for i in range(N_dealers):
            agent = DrugAgent(i + N_citizens, self, "dealer")
            self.schedule.add(agent)
            x = self.random.randrange(self.grid.width)
            y = self.random.randrange(self.grid.height)
            self.grid.place_agent(agent, (x, y))

        for i in range(N_police):
            agent = DrugAgent(i + N_citizens + N_dealers, self, "police")
            self.schedule.add(agent)
            x = self.random.randrange(self.grid.width)
            y = self.random.randrange(self.grid.height)
            self.grid.place_agent(agent, (x, y))

        for i in range(N_data_collectors):
            agent = DrugAgent(i + N_citizens + N_dealers + N_police,
                              self,
                              "data-collector")
            self.schedule.add(agent)
            x = self.random.randrange(self.grid.width)
            y = self.random.randrange(self.grid.height)
            self.grid.place_agent(agent, (x,y))

    def step(self):
        """Advance the model by one step."""
        self.schedule.step()

def agent_portrayal(agent):
    portrayal = {}  # Initialize the portrayal dictionary
    
    if agent.role == "citizen":
        portrayal["Color"] = "blue"
    elif agent.role == "dealer":
        portrayal["Color"] = "red"
    elif agent.role == "police":
        portrayal["Color"] = "green"
    elif agent.role == "data-collector":
        portrayal["Color"] = "yellow"
    elif agent.role == "drug-user":
        portrayal["Color"] = "orange"
    
    portrayal["Shape"] = "circle"
    portrayal["Filled"] = True
    portrayal["r"] = 0.5
    
    return portrayal

# Set up the visualization components
grid = CanvasGrid(agent_portrayal, 10, 10, 500, 500)  # Adjust grid size as needed

# Create the server to run the simulation
server = ModularServer(
    DrugModel,
    [grid],
    "Drug Simulation",
    {
     "N_citizens": 100,
     "N_dealers": 50,
     "N_police": 20,
     "N_data_collectors": 10}
)

server.port = 8521  # The default port is set to 8521.
server.launch()