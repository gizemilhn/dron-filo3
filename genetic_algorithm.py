import random
import numpy as np
from deap import base, creator, tools, algorithms
from astar import astar
from utils import calculate_energy, calculate_distance

def create_route_optimizer(drones, deliveries, no_fly_zones):
    """Create a genetic algorithm optimizer for drone routes"""
    
    # Create fitness and individual classes
    creator.create("FitnessMin", base.Fitness, weights=(-1.0,))  # Minimize total distance
    creator.create("Individual", list, fitness=creator.FitnessMin)
    
    toolbox = base.Toolbox()
    
    # Attribute generator
    toolbox.register("attr_delivery", random.randint, 0, len(deliveries) - 1)
    
    # Structure initializers
    toolbox.register("individual", tools.initRepeat, creator.Individual, 
                     toolbox.attr_delivery, n=len(deliveries))
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    
    def evaluate_route(individual):
        """Evaluate a delivery route"""
        total_distance = 0
        total_energy = 0
        
        # Calculate path distances
        for i in range(len(individual) - 1):
            p1 = individual[i]['pos']
            p2 = individual[i + 1]['pos']
            total_distance += calculate_distance(p1, p2)
        
        # Add return to start position if needed
        if individual:
            total_distance += calculate_distance(individual[-1]['pos'], individual[0]['pos'])
        
        # Calculate fitness score
        fitness = (
            total_distance * -1.0 +  # Minimize distance
            sum(d['priority'] * 100 for d in individual)  # Maximize priority deliveries
        )
        
        return (fitness,)  # Return as tuple for DEAP
    
    toolbox.register("evaluate", evaluate_route)
    toolbox.register("mate", tools.cxOrdered)
    toolbox.register("mutate", tools.mutShuffleIndexes, indpb=0.1)
    toolbox.register("select", tools.selTournament, tournsize=3)
    
    return toolbox

def optimize_routes(drones, deliveries, no_fly_zones, pop_size=100, n_gen=50):
    """Run the genetic algorithm to optimize delivery routes"""
    toolbox = create_route_optimizer(drones, deliveries, no_fly_zones)
    
    # Create initial population
    pop = toolbox.population(n=pop_size)
    
    # Track best solution
    hof = tools.HallOfFame(1)
    
    # Run algorithm
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", np.mean)
    stats.register("min", np.min)
    
    pop, logbook = algorithms.eaSimple(pop, toolbox, cxpb=0.7, mutpb=0.2, 
                                      ngen=n_gen, stats=stats, halloffame=hof,
                                      verbose=True)
    
    return hof[0], logbook