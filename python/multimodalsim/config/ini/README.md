# Config files

## cap_requests_generator.ini

Used by CAPRequestsGenerator, CAPFormatter and AvailableConnectionsExtractor.

* **connections**:
  * **max_connection_time** *(int or float)*: Given two rows of the CAP 
    file associated with the same passenger, this parameter determines the 
    maximum time allowed between the rows for them to be recognized as 
    legs of the same trip.

* **requests**:
  * **release_time_delta** *(int or float)*: Time interval between the 
    release time and the boarding time.
  * **ready_time_delta** *(int or float)*: Time interval between the 
    ready time and the boarding time.
  * **due_time_delta** *(int or float)*: Time interval between the 
    due time and the arrival time.

* **cap_columns** *(str)*: Column names of the CAP file.


## coordinates_osrm.ini

Used by CoordinatesOSRM.

* **parameters**:
  * **url**: URL to the OSRM server used by **CoordinatesOSRM**.


## data_analyzer.ini

Used by FixedLineDataAnalyzer.

* **parameters**:
  * **ghg_e** *(int or float)*: Quantity of greenhouse gases emitted by a 
    vehicle by distance unit.
  * **events_table** *(str)*: Name of the events table
  * **vehicles_table** *(str)*: Name of the vehicles table
  * **trips_table** *(str)*: Name of the trips table


## data_collector.ini

Used by StandardDataCollector.

* **vehicles** *(str)*: Column names of the vehicles output file.
* **trips** *(str)*: Column names of the trips output file.
* **events** *(str)*: Column names of the events output file.


## gtfs_data_reader.ini

Used by GTFSReader.

* **trips** *(int)*: Positions of the columns in the trips.txt file of the 
  GTFS folder.


## optimization.ini

Used by Optimization.

* **general**:
  * **freeze_interval** *(int or float)*:  Time interval during which the 
    current state of 
    the environment is frozen at each optimization.
  * **multiple_optimize_events** *(bool)*: If this parameter is set to true,  
    then it is possible to create (and process) multiple Optimize events for 
    the same simulation time unit. In other words, multiple optimizations 
    may occur at the same simulation time. On the other hand, it is set to 
    false, then at most one Optimize event is created at a given simulation 
    time. Moreover, this Optimize event is processed after all the other 
    events scheduled for the same time are processed.
  * **batch** *(int or float)*: Minimum time interval between two 
    optimizations. All the Optimize events that are planned to happen during 
    this time interval are batched into one Optimize event that takes place 
    at the end of the time interval. For example, if **batch** is set to 5, 
    and two Optimize events are created at time 0 and 3, then these 
    Optimize events will be replaced with only one Optimize event that is 
    processed at time 5. By default, there is no minimum time interval 
    between optimizations. 
* **asynchronous**:
  * **asynchronous** *(bool)*: If true, then optimization takes place in a 
    thread different from the thread of the simulation. 
  * **max_optimization_time** *(int or float)*: Maximum time allowed for an 
    optimization. After the time has elapsed, the optimization process is 
    terminated. Note that this applies only if **asynchronous** is true.
  * **termination_waiting_time** *(int or float)*: Waiting time until the 
    optimization process is killed after being terminated.


## simulation.ini

Used by Simulation.

* **general**:
  * **max_time** *(int or float)*: The time at which the simulation ends.
    If this field is left empty, the simulation will end after processing all 
    the events in the event queue.
* **time_sync_event**:
  * **time_step** *(int or float)*: The time interval (in terms 
    of simulation time) at which a recurrent time synchronization event 
    (RecurrentTimeSyncEvent) is added to the queue (and processed). For example,
    if this parameter is set to 5, an event RecurrentTimeSyncEvent is 
    processed every 5 simulation time units. If this parameter is left empty, 
    no RecurrentTimeSyncEvent is created. 
  * **speed** *(int or float)*: The speed at which the 
    recurrent time synchronization events (RecurrentTimeSyncEvent) are 
    processed. It is the factor that converts simulation time into real 
    time. For example, if the value of **time_step** is 5 and 
    **speed** is 10, then a RecurrentTimeSyncEvent is processed every 5 
    simulation time units, but every 5/10 = 0.5 seconds in terms of real 
    time. By default, the value of speed is 1, i.e., 1 simulation time unit 
    corresponds to 1 second.
* **update_position_event**:
  * **time_step** *(int or float)*: The time interval at which the position 
    (i.e., the coordinates) of the vehicles is updated. 
