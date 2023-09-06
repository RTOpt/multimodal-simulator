# multimodalsim

## Description

multimodalsim is a package to perform discrete-event simulations of a public transportation system.


## Setup

To install the package, execute the following command in a terminal:

    python setup.py install


## Simulation Initialization

### Optimization

The optimization algorithm that will be used by the simulation is determined by an object of type **Optimization**. 
This object is initialized with a **Splitter**, that splits the trips into legs, and a **Dispatcher**, 
that assigns the legs to routes. The **Dispatcher** may receive as argument information about the network 
(e.g., g in the example below).

For example:

    splitter = OneLegSplitter()
    dispatcher = ShuttleGreedyDispatcher(g)
    opt = Optimization(dispatcher, splitter)

### Simulation

The simulation is initialized by creating an object of type Simulation that receives as arguments an object of type **Optimization**, 
a list of Trip objects, a list of Vehicle objects and, optionally, a network.

For example:

    simulation = Simulation(opt, trips, vehicles, network=g)
    
## Simulation Execution

To execute the simulation, call the **simulate()** method of the Simulation object.
   
For example:
    
    simulation.simulate()

## Reading data:

The vehicles, the trips and the network can be read from input files using a DataReader object. 

For example:

    data_reader = BusDataReader(requests_file_path, vehicles_file_path)
    vehicles = data_reader.get_vehicles()
    trips = data_reader.get_trips()


## Visualizer

An object inherited from the base class **Visualizer** can be provided to Simulation through the optional parameter **visualizer** of its constructor.
The **visualize_environment()** method of Visualizer is called at the beginning of each iteration of the simulation and prints information about the environment.

For example:

    visualizer = ConsoleVisualizer()
    simulation = Simulation(opt, trips, vehicles, visualizer=visualizer)


## Examples
 
Example programs can be found in the folder *examples*.


## Log level

By default, the log level is set to INFO. It can be modified by calling the **setLevel()** method of the root logger.

For example:

    import logging

    logging.getLogger().setLevel(logging.DEBUG)
    

