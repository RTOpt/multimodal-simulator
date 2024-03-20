# Examples

This folder contains complete examples of how to create and execute a 
simulation. Each example is based on the following steps:

1. Read data from files
2. Select an optimization algorithm
3. Create a simulation
4. Execute the simulation

Examples are provided for fixed line transportation services (for example, 
bus lines) and for shuttles (for example, taxis).

## Fixed line

### fixed_line.py

This is an example of a unimodal fixed lines simulation. The dispatching 
algorithm is provided by the FixedLineDispatcher 
(/multimodalsim/optimization/fixed_line/fixed_line_dispatcher.py), which 
assigns each leg to the route with the earliest arrival time at destination.
Note that the OneLegSplitter is used to create a unique leg for each trip.

The data of the simulation are read from csv files with the help of the 
BusDataReader.

### fixed_line_gtfs.py

This is an example of a unimodal fixed lines simulation that makes use of 
schedules written in the GTFS (General Transit Feed Specification) format. 
As in the previous example, the optimization algorithm is based on the 
FixedLineDispatcher and the OneLegSplitter.

The information about the vehicle is extracted from GTFS files with the 
help of the GTFSReader.

### fixed_line_gtfs_multimodal.py

This is an example of a multimodal fixed lines simulation that makes use of 
schedules written in the GTFS (General Transit Feed Specification) format. 
As in the previous examples, the simulation uses the FixedLineDispatcher. 
However, the MultimodalSplitter is used instead of the OneLegSplitter. The 
MultimodalSplitter splits a trip into a series of legs according to a 
shortest path algorithm.

### fixed_line_travel_times.py

This is an example of a multimodal fixed lines simulation in which the 
actual travel times are different from the planned travel times. On one 
hand, the planned travel times are known at the time of optimization and 
are used by the optimization algorithm to make decisions. On the other hand,
the actual travel times are only known by the simulation and are used to 
determine the actual arrival time of the vehicles.

As in the previous two examples, the planned travel times are extracted 
from GTFS files with the help of the GTFSReader. On the other hand, the 
actual travel times are read from a csv file by the MatrixTravelTimesReader.
The csv file specifies the actual travel time that a vehicle 
requires to go from an origin to a destination.

## Shuttle

### shuttle_hub_simple_dispatcher.py

This is an example of the use of the dispatcher when working with shuttles. 
It is based on the ShuttleHubSimpleDispatcher 
(/multimodalsim/optimization/shuttle/shuttle_hub_simple_dispatcher.py). 
This dispatcher implements a simple optimization algorithm that 
assigns to the vehicles available at the hub the trips of the environment 
that have not been assigned yet. Moreover, each vehicle serves at most one 
trip at a time. 

This example does not make use of a network (e.g., a graph that indicates 
the distance/travel time between the different locations). The travel time 
between any pair of nodes is considered constant.

For more details, see the comments in 
/multimodalsim/shuttle/shuttle_simple_dispatcher.py.

### shuttle_hub_simple_network_dispatcher.py

This example demonstrates how to use the dispatcher with a 
network (e.g., a graph that indicates the distance/travel time between the 
different locations). It is based on the ShuttleHubSimpleNetworkDispatcher 
(/multimodalsim/optimization/shuttle/shuttle_hub_simple_network_dispatcher.
py), which implements the same optimization algorithm as the 
ShuttleHubSimpleDispatcher. The only difference is that the travel 
time between any pair of nodes is now given by the network graph.

For more details, see the comments in 
/multimodalsim/shuttle/shuttle_hub_simple_network_dispatcher.py.