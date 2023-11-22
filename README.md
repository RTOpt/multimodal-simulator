# multimodalsim

## Description

multimodalsim is a package to perform discrete-event simulations of a 
transportation system.

## Simulation

### General Description

multimodalsim generates multi-modal discrete events simulations of a 
transportation system in which vehicles transport passengers from an origin 
to a destination.

### Agents

Two types of agents interact in a simulation: the trips and 
the vehicles.

#### Trips (passengers)

Each trip is associated with an object of type **Trip**, which inherits 
from the base class Request. 

An object of type Request essentially consists of a request to transport 
one or more passengers from a given origin to a given destination. Moreover, a 
request contains time information that specifies the period over which the 
passengers should be transported:
* Release time: the time at which appears in the system (i.e., is added to 
  the environment).
* Ready time: the time from which the passengers are available to be 
  picked up.
* Due time: the time at which the passengers should have arrived at 
  destination.

In addition to all the information contained in a request, an object of 
type Trip specifies the series of locations by which the passengers stop
during their trip. Each segment of a trip (i.e., a successive pair of locations)
is called a leg and is associated with an object of type **Leg**, which 
also inherits from the base class Request. If a trip has more than one leg,
then it is said to be multimodal; otherwise, it is unimodal.


#### Vehicles

Each vehicle is associated with an object of type Vehicle. 

* Route
* Stop
* Location

### Environment



### State

### Events

A simulation is based on a sequence of events. Each event is processed at a 
particular time and has a specific effect on the environment. No change in 
the system occurs between two consecutive events.

There are three different types of events: optimization events, passenger 
events and vehicle events.

A flow chart illustrating the relationship between the different events can 
be found on page 2 of multimodal-simulator/docs/flow_charts.pdf.

#### 

#### Passenger events



#### Vehicle events

### Events queue

The events of the simulation are stored in a priority queue. The priority 
of the queue is determined by the time of the event (i.e., Event.time), as 
well as its priority (i.e., Event.priority). The events with the smallest time 
are processed first. Among the events that have the same time, the ones with 
the lowest priority are processed first.


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
    dispatcher = ShuttleHubSimpleDispatcher(g)
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
(/multimodalsim/optimization/dispatcher.py) and that has a **dispatch** 
method. This method is called whenever the OptimizeEvent is processed (and 
an optimization is required). It has for objective to optimize the vehicle 
routing and the trip-route assignment. In other words, it determines the 
list of next stops (i.e., the route) of each vehicle and 
which leg is assigned to which route.

The **dispatch** method takes a State object as argument. Since 
a State object is essentially a deep copy of the environment (see 
**Environment** and **State** above), it is in particular possible to 
extract from it information about the routes and the legs. This 
information can then be used to construct and solve an optimization model.

The output of the **dispatch** method is an object of type 
**OptimizationResult** (/multimodalsim/optimization/optimization.py). This 
object essentially contains a copy of the Trip objects and the Vehicle objects 
that were modified by the optimization algorithm of the **dispatch** method.

Note that overriding the **dispatch** method of the base class 
**Dispatcher** directly requires a relatively advanced knowledge of the 
package. In many cases, it is sufficient to use the default **dispatch** 
method and override the **prepare_input** and the **optimize** methods. For 
more details, see the next subsection.

#### Default **dispatch** method

The default **dispatch** method was created with the purpose of facilitating 
the integration of optimization algorithms to simulations. In particular, 
it makes it possible to translate optimization results into a language 
understandable by the simulator without having to understand all the 
intricate details of the simulator.

The predefined **dispatch** method calls successively the following 
three methods:
* **prepare_input**: 
  * Description: This method selects from the state the legs and the 
    routes that you want to be considered by the optimization algorithm. 
    For example, you may want to include only the legs that are not 
    already assigned to a route.
  * Default behavior: All the legs and all the routes of the environment 
    are optimized.
  * Input: 
    * state (**State**): the state of the environment at the time of 
      optimization (see 
      **State** above)
  * Output:
    * selected_next_legs (**list** of **Leg** objects): list of the next legs 
      selected to be considered by the **optimize** method (see bullet point 
      below). A "next leg" is the first leg of the list Trip.next_legs.
    * selected_routes: (**list** of **Route** objects): list of the routes 
      selected to be considered by the **optimize** method (see bullet point
      below).
* **optimize**:
  * Description: This method determines the vehicle routing and the 
    trip-route assignment. In other words, this is where the optimization 
    algorithm should be coded. 
  * Default behavior: This method has no default behavior. It must be 
    overriden.
  * Input:
    * selected_next_legs (**list** of **Leg** objects): list of the next legs 
      selected to be considered by the optimization algorithm (i.e., first 
      output of **prepare_input**).
    * selected_routes (**list** of **Route** objects): list of the 
      routes selected to be considered by the optimization algorithm (i.e., 
      second output of **prepare_input**).
    * current_time: Integer equal to the current time of the state of the 
      environment. Note that the current time of the state may be different 
      from the current time of the environment due to the "freeze interval".
      (See **freeze_interval** of **Optimization** above.)
    * state (**State**): the state of the environment at the time of 
      optimization (see **State** above)
  * Output:
    * optimized_route_plans (**list** of **OptimizedRoutePlan** objects): 
      List of the OptimizedRoutePlan objects (see next bullet point).
  * **OptimizedRoutePlan**: In the **optimize** method, a list of  
    OptimizedRoutePlan objects that contain the results of optimization 
    must be created. More precisely, for each route that should be modified 
    by the optimization, an object of type OptimizedRoutePlan specifies the 
    departure time of the current stop, the list of next stops and the legs 
    assigned to the route.
* **process_optimized_route_plans**:
  * Description: This method "translates" the results of optimization (i.e.,
    the optimized route plans returned by the **optimize** method) into the 
    "language" of the simulator (i.e., **Route**, **Stop**, **Vehicle**, 
    **Trip**, etc.).
  * Default behavior: It assigns the legs to the routes and modifies the 
    next stops of a route according to the list of OptimizedRoutePlan 
    objects returned by the **optimize** method. This default behavior 
    should be sufficient for most applications. In general, there is no 
    need to override this method.

#### Examples

A few examples of dispatchers are provided with the package, but in general,
users will probably want to create their own Dispatcher object, whether by 
using or not the default **dispatch** method.

##### Example 1: ShuttleHubSimpleDispatcher

The ShuttleHubSimpleDispatcher 
(/multimodalsim/shuttle/shuttle_hub_simple_dispatcher.
py) is a simple example that demonstrates how to use the ShuttleDispatcher.
It is based on a simple optimization algorithm that assigns to the vehicles 
available at the hub the trips of the environment that have not been 
assigned yet. Moreover, each vehicle serves at most one trip at a time.

This example does not make use of a network (e.g., a graph that indicates 
the distance/travel time between the different locations). The travel time 
between any pair of nodes is considered constant.

For more details, see the comments in 
/multimodalsim/shuttle/shuttle_simple_dispatcher.py.

##### Example 2: ShuttleHubSimpleNetworkDispatcher

The ShuttleHubSimpleNetworkDispatcher 
(/multimodalsim/shuttle/shuttle_hub_simple_network_dispatcher.py) is a 
simple example that demonstrates how to use the 
ShuttleDispatcher with a network (e.g., a graph that indicates the 
distance/travel time between the different locations). It is based on 
the same simple optimization algorithm as the ShuttleHubSimpleDispatcher. The 
only difference is that the travel time between any pair of nodes is now 
given by the network.

For more details, see the comments in 
/multimodalsim/shuttle/shuttle_hub_simple_network_dispatcher.py.

##### Example 3: ShuttleGreedyDispatcher

The ShuttleGreedyDispatcher 
(/multimodalsim/shuttle/shuttle_greedy_dispatcher.py) is a more complex 
example. It is based on an 
optimization algorithm that assigns the trips to the vehicles in a greedy way.

##### Example 4: FixedLineDispatcher

## Examples
 
Example programs can be found in the folder *examples*.


## Log level

By default, the log level is set to INFO. It can be modified by calling the 
**setLevel()** method of the root logger.

For example:

    import logging

    logging.getLogger().setLevel(logging.DEBUG)
    

