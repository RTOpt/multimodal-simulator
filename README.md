# multimodalsim

## Description

multimodalsim is a package to perform discrete-event simulations of a 
transportation system.

## Simulation

### General Description

multimodalsim generates multi-modal simulations of a transportation system 
in which vehicles transport passengers from an origin to a destination.

### Agents

#### Trips (passengers)

* Requests
* Legs

#### Vehicles

* Route
* Stop
* Location

### Environment

### State

### Events

#### Passenger events

#### Vehicle events

### Events queue


### Main loop


### Optimize event


## Setup

To install the package, execute the following command in a terminal:

    python setup.py install


## Simulation Initialization

### Optimization

The optimization algorithm that will be used by the simulation is determined by
an object of type **Optimization** (see Optimization below). This object is 
initialized with a **Splitter**, that splits the trips into legs, and a 
**Dispatcher**, that assigns the legs to routes. The **Dispatcher** may 
receive as argument information about the network (e.g., g in the example 
below).

For example:

    splitter = OneLegSplitter()
    dispatcher = ShuttleSimpleDispatcher(g)
    optimization = Optimization(dispatcher, splitter)

### Simulation

The simulation is initialized by creating an object of type **Simulation** 
(/multimodalsim/simulator/simulation.py) that receives as arguments an 
object of type **Optimization**, a list of Trip 
objects, a list of Vehicle objects and, optionally, a network.

For example:

    simulation = Simulation(optimization, trips, vehicles, network=g)
    
## Simulation Execution

To execute the simulation, call the **simulate** method of the Simulation 
object.
   
For example:
    
    simulation.simulate()

## Reading data:

The vehicles, the trips and the network can be read from input files using a 
DataReader object. 

For example:

    data_reader = BusDataReader(requests_file_path, vehicles_file_path)
    vehicles = data_reader.get_vehicles()
    trips = data_reader.get_trips()


## Environment observer

An object that inherits from the base class **EnvironmentObserver** 
(/multimodalsim/observer/environment_observer.py) can be provided to
Simulation through the optional parameter **environment_observer** of its 
constructor. The environment observer is responsible for collecting data and 
displaying the results at each iteration of the simulation.

An environment observer essentially consists of a (list of) visualizer(s) and a
(list of) data collector(s), that are passed as arguments of the constructor.

For example, you can initialize the EnvironmentObserver object with a single 
data collector and a single visualizer:

    environment_observer = EnvironmentObserver(data_collectors=data_collector,
                                               visualizers=visualizer)

You can also initialize it with a list of data collectors and visualizers:

    environment_observer = EnvironmentObserver(data_collectors=[data_collector1, 
                                                                data_collector2,
                                                                data_collector3]
                                               visualizers=[visualizer1, 
                                                            visualizer2])

### Data collector

A data collector is an object that inherits from the base class 
**DataCollector** (/multimodalsim/observer/data_collector.py)  and that 
overrides the method **collect**. This method is called at the end of each 
iteration of the simulation (i.e., after the current event has been processed).

The role of the data collector is to collect specific data from the 
environment during the simulation. Which data will be collected and where 
(i.e., in which data structure) the data will be saved should be specified 
in the **collect** method.

#### StandardDataCollector

An example of data collector is the StandardDataCollector 
(/multimodalsim/observer/data_collector.py). It stores information about 
the vehicles, the trips and the processed events in a Pandas DataFrame that 
can then be exported in a .csv file.

The StandardDataCollector can be instantiated as follows:

    data_collector = StandardDataCollector()

### Visualizer

A visualizer is an object that inherits from the base class **Visualizer** 
(/multimodalsim/observer/visualizer.py) and that overrides 
**visualize_environment** the method. This method is called at  the 
beginning of each iteration of the simulation (i.e., after the current 
event has been processed).

The role of the visualizer is to display specific information from the 
environment during the simulation. The specific data and the way it will be 
displayed (e.g., console, GUI, etc.) should be specified in the 
**visualize_environment** method.

#### ConsoleVisualizer

An example of a visualizer is the ConsoleVisualizer 
(/multimodalsim/observer/visualizer.py). It displays information about the 
vehicles, the trips and the processed events in the console.

The ConsoleVisualizer can be instantiated as follows:

    visualizer = ConsoleVisualizer()
    

### StandardEnvironmentObserver

The StandardEnvironmentObserver 
(/multimodalsim/observer/environment_observer.py) is an environment observer 
that consists of a StandardDataCollector and a ConsoleVisualizer.

The StandardEnvironmentObserver can be instantiated as follows:

    environment_observer = StandardEnvironmentObserver()

## Optimization

To create a new simulation, it is necessary to specify an optimization 
algorithm that will determine how the trips should be assigned to the 
vehicles as well as the route followed by each vehicle. The Simulation object 
has access to this algorithm through an **Optimization** 
(/multimodalsim/optimization/optimization.py) object that is passed
to it as the first argument of its constructor. For example,

    simulation = Simulation(optimization, trips, vehicles, network=g)

The **Optimization** object is essentially composed of a splitter, that 
splits the trips into legs, and a dispatcher, that assigns the legs to 
routes. When you create the **Optimization** object, you have to specify 
the splitter and the dispatcher to be used. For example,

    optimization = Optimization(dispatcher, splitter=splitter)

If no splitter is passed as argument to the constructor of **Optimization**,
then a **OneLegSplitter** (see below) is used by default. 

### Splitter

A splitter is an object that inherits from the base class **Splitter** 
(/multimodalsim/optimization/splitter.py) and that overrides the 
**split** method. This method is called when the PassengerRelease event is 
processed (i.e., when a new trip is released in the simulation) if no 
predefined leg is already assigned to the Trip object. 

The **split** method takes a Trip object and a State object as arguments, 
splits the trip into legs, and returns the legs as a list of Leg objects. 

The legs of a trip are each associated with a pair origin-destination. The 
origin of the first leg must be equal to the origin of the trip, and the 
destination of the last leg must be equal to the destination of the trip. 
Moreover, the origin of any given leg must be equal to the destination of 
the previous leg in the list. For example, the trip with origin 1 and 
destination 2 is split into three legs:
* Input: trip -> (1, 2)
* leg1 -> (1, 3)
* leg2 -> (3, 4)
* leg3 -> (4, 2)
* Output: [leg1, leg2, leg3]

Note that the splitter does not specify the precise route (i.e., list of 
stops) that composes the trip or which vehicle is assigned to which leg. 
This is the responsibility of the dispatcher (see **Dispatcher** below).

#### OneLegSplitter

The OneLegSplitter is a splitter that splits the trip in into a single leg. 
For example, the trip with origin 1 and destination 2 is split as follows:
* Input: trip -> (1, 2)
* leg -> (1, 2)
* Output: [leg]
In a unimodal, single-leg setting, the OneLegSplitter should be sufficient 
in most cases.

Note that a OneLegSplitter is created by default if no argument is passed to 
the **splitter** parameter of **Optimization** (see **Optimization** above).

### Dispatcher

A dispatcher is an object that inherits from the base class **Dispatcher** 
(/multimodalsim/optimization/dispatcher.py) and that overrides the 
**dispatch** method. This method is called whenever the OptimizeEvent is 
processed (and an optimization is required). It has for objective to 
optimize the vehicle routing and the trip-route assignment. In other words,
it determines the list of next stops (i.e., the route) of each vehicle and 
which leg is assigned to which route (or vehicle).

The **dispatch** method takes a State object as argument. Since 
a State object is essentially a deep copy of the environment (see 
**Environment** and **State** above), it is in particular possible to 
extract from it information about the vehicles and the trips. This 
information can then be used to construct and solve and optimization model.

The output of the **dispatch** method is an object of type 
**OptimizationResult** (/multimodalsim/optimization/optimization.py). This 
object essentially contains a copy of the Trips and the Vehicle objects that 
were modified by the optimization algorithm of the **dispatch** method.

Note that overriding the **dispatch** method of the base class 
**Dispatcher** directly requires a relatively advanced knowledge of the 
package. If your simulation involves the use of shuttle-like vehicles, you may 
find it easier to start with a ShuttleDispatcher (see **ShuttleDispatcher** 
below).

A few examples of dispatchers are provided with the package (see, **Example 
1** and **Example 2**), but in general, users will probably want to create 
their own Dispatcher object, whether it inherits from ShuttleDispatcher 
(see below) or from the base class Dispatcher directly.

#### ShuttleDispatcher

The ShuttleDispatcher (/multimodalsim/optimization/dispatcher.py) is a
dispatcher that was created with the purpose of facilitating the 
integration of optimization algorithms to simulations with shuttles (or 
shuttle-like vehicles). In particular, it makes it easier to translate the 
results of optimization into a language understandable by the simulator.

The predefined **dispatch** method calls successively the following 
three methods:
* **prepare_input**: 
  * Description: This method extracts from the state the trips and the 
    vehicles that you want to be considered by the optimization algorithm. 
    For example, you may want to include only the trips that are not 
    already assigned to a vehicle.
  * Default behavior: All the trips and all the vehicles of the 
    environment are optimized.
  * Input: 
    * state (**State**): the state of the environment at the time of 
      optimization (see 
      **State** above)
  * Output:
    * trips (**list** of **Trip** objects): list of the trips that will be 
      considered by the **optimize** method (see bullet point below).
    * vehicles: (**list** of **Vehicle** objects): list of the vehicles that 
      will be considered by the **optimize** method (see bullet point below).
* **optimize**:
  * Description: This method determines the vehicle routing and the 
    trip-route assignment. In other words, this is where the optimization 
    algorithm should be coded. 
  * Default behavior: This method has no default behavior. It must be 
    overriden.
  * Input:    
    * trips (**list** of **Trip** objects): List of the trips to be 
      considered by the optimization algorithm (i.e., first output of 
      **prepare_input**).
    * vehicles (**list** of **Vehicle** objects): List of the vehicles to 
      be considered by the optimization algorithm (i.e., second output of 
      **prepare_input**).
    * current_time: Integer equal to the current time of the state of the 
      environment. Note that the current time of the state may be different 
      from the current time of the environment due to the "freeze interval".
      (See **freeze_interval** of **Optimization** above.)
    * state (**State**): the state of the environment at the time of 
      optimization (see **State** above)
  * Output:
    * stops_list_by_vehicle_id (**dict**): Dictionary mapping the vehicle 
      ID of each vehicle that was modified by the optimization to a list 
      of its current and next stops. For each stop, the stop ID as well as 
      the arrival and the departure times of the vehicle must be 
      specified. For a detailed description of the structure of this object,
      see the comments after the method header
      in /multimodalsim/optimization/dispatcher.py.
    * trip_ids_by_vehicle_id (**dict**): Dictionary mapping the vehicle 
      ID of each vehicle that was modified by the optimization to a list 
      of the trips assigned to the vehicle. For a detailed description of the 
      structure of this object, see the comments after the method header 
      in /multimodalsim/optimization/dispatcher.py.
* **process_output**:
  * Description: This method "translates" the results of optimization (i.e.,
    the output of the **optimize** method) into the "language" of the 
    simulator (i.e., **Route**, **Stop**, **Vehicle**, **Trip**, etc.).
  * Default behavior: It assigns the legs to the routes and modifies the 
    next stops of a route according to the output of the **optimize** 
    method. This default behavior should be sufficient for most 
    applications of the **ShuttleDispatcher**. In most cases, there is no 
    need to override this method.

##### Example 1: ShuttleSimpleDispatcher

##### Example 2: ShuttleSimpleNetworkDispatcher


## Examples
 
Example programs can be found in the folder *examples*.


## Log level

By default, the log level is set to INFO. It can be modified by calling the 
**setLevel()** method of the root logger.

For example:

    import logging

    logging.getLogger().setLevel(logging.DEBUG)
    

