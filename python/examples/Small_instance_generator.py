from multimodalsim.reader.gtfs_generator import GTFSGenerator
from multimodalsim.reader.available_connections_extractor import AvailableConnectionsExtractor
from multimodalsim.reader.requests_generator import CAPRequestsGenerator
import logging
import os
import argparse
import csv
import pandas as pd
import numpy as np
from collections import defaultdict
from operator import itemgetter
import copy

# base_folder=r"C:\Users\kklau\Desktop\Simulator"
logger = logging.getLogger(__name__)

### This file generates partial data of the day November 1st 2019 to allow for testing on a medium size real instance.
### The main trip id is '2790970' from line 42O. All passengers boarding this bus will be included.
### All buses from lines transferring passengers from/to this trip will be included as well.
small=False
only_transfers=False
main_trip_id="2790970"
max_distance = 0.5 #connection max distance in km
if small:
    nb_transfers=3
    small_name="_small"
    small_folder="-small"
else: 
    nb_transfers=5
    small_name=""
    small_folder=""
###CAP files
###Find relevant passengers and tripsand write into new smaller CAP file
cap_file_path_old=os.path.join("D:","","donnees","New donnees","20191101.csv")
cap_file_path_generated=os.path.join("D:",'',"donnees","Data_Simulator","20191101_relevant"+small_name+".csv")


# Read .csv file cap_file_path_old and find relevant passengers.
# If these passengers transfer, we take into account the transfering trips as well.
# Write a new CAP file with only the relevant passengers.

# Read the cap file and find the relevant trips and passengers
relevant_trips=[main_trip_id]
lines_to_use=[]
with open(cap_file_path_old, 'r') as file:
    # Read the header
    header=file.readline()
    # Find at which position the passenger_id, trip_id and validation_time are
    header_split=header.strip().split(";")
    passenger_id_index=header_split.index("C_NUM_SUPPORT")
    trip_id_index=header_split.index("S_VEHJOBID_IDJOURNALIER")
    validation_time_index=header_split.index("C_SECONDE28")
    lign_numer_index=header_split.index("S_LIGNE")
    # Sort lines by passenger_id and validation time
    lines=file.readlines()
    lines_sorted=[]
    for i in range(len(lines)):
        line=lines[i]
        line_split=line.strip().split(";")
        passenger_id=line_split[passenger_id_index]
        validation_time=line_split[validation_time_index]
        lines_sorted.append((passenger_id,validation_time,line,i))
    lines_sorted=sorted(lines_sorted, key=itemgetter(0,1))
    lines=[(lines_sorted[i][2],lines_sorted[i][3]) for i in range(len(lines_sorted))]
    written_lines=[]
    transfers=0
    #For each line, check if the trip_id is relevant and if so save the line
    for i in range(len(lines)):
        line=lines[i][0]
        line_split=line.strip().split(";")
        trip_id=line_split[trip_id_index]
        if trip_id==main_trip_id:
            if (not only_transfers) and (lines[i][1] in written_lines)==False:
                written_lines.append(lines[i][1])
            passenger_id=line_split[passenger_id_index]
            validation_time=int(line_split[validation_time_index])
            lign_number=line_split[lign_numer_index]
            if i>0 and (lines[i-1][1] in written_lines)==False:
                passenger_id_prev=lines[i-1][0].strip().split(";")[passenger_id_index]
                validation_time_prev=int(lines[i-1][0].strip().split(";")[validation_time_index])
                lign_number_prev=lines[i-1][0].strip().split(";")[lign_numer_index]
                trip_id_prev=lines[i-1][0].strip().split(";")[trip_id_index]
                if (trip_id_prev!="") and (transfers<nb_transfers) and passenger_id==passenger_id_prev and (validation_time-validation_time_prev<5400) and lign_number!=lign_number_prev: #transfer so need to keep the transferring trip
                    relevant_trips.append(trip_id_prev)
                    # print('trip_id_prev:',trip_id_prev)
                    written_lines.append(lines[i-1][1])
                    transfers+=1
                    if only_transfers and (lines[i][1] in written_lines)==False:
                        written_lines.append(lines[i][1])
            if i+1<len(lines) and (lines[i+1][1] in written_lines)==False:
                passenger_id_next=lines[i+1][0].strip().split(";")[passenger_id_index]
                validation_time_next=int(lines[i+1][0].strip().split(";")[validation_time_index])
                lign_number_next=lines[i+1][0].strip().split(";")[lign_numer_index]
                trip_id_next=lines[i+1][0].strip().split(";")[trip_id_index]
                if (trip_id_next!="") and (transfers<nb_transfers) and passenger_id==passenger_id_next and (validation_time_next-validation_time<5400) and lign_number!=lign_number_next: #transfer so need to keep the transferring trip
                    # print('trip_id_next:',trip_id_next)
                    relevant_trips.append(trip_id_next)
                    written_lines.append(lines[i+1][1])
                    transfers+=1
                    if only_transfers and (lines[i][1] in written_lines)==False:
                        written_lines.append(lines[i][1])
print('Number of transfers:',transfers)
# Write the relevant lines into a new file
lines_to_write=[lines[i] for i in range(len(lines)) if lines[i][1] in written_lines]
lines_to_write=sorted(lines_to_write, key=itemgetter(1))
with open(cap_file_path_generated, 'w') as file:
    file.write(header)
    for line in lines_to_write:
        file.write(line[0])

relevant_trips = list(set(relevant_trips))
###Next we need to figure out from the GTFS files which trips are relevant
##Location of the GTFS files
gtfs_folder_old=os.path.join("data","fixed_line","gtfs","gtfs2019-11-01")
gtfs_folder_generated=os.path.join("data","fixed_line","gtfs","gtfs-generated"+small_folder)

#Create Calendar_dates.txt file
calendar_dates_file_path=os.path.join(gtfs_folder_generated,"calendar_dates.txt")
with open(calendar_dates_file_path, 'w') as file:
    file.write("service_id,date,exception_type\n")
    file.write("Sem,20191101,1\n")

# Create trips.txt file
trips_file_path=os.path.join(gtfs_folder_old,"trips.txt")
trips_file_path_generated=os.path.join(gtfs_folder_generated,"trips.txt")
with open(trips_file_path, 'r') as file:
    #Read the header
    header=file.readline()
    #Find at which position the trip_id is
    header_split=header.strip().split(",")
    trip_id_index=header_split.index("trip_id")
    #Real all remaining lines
    lines=file.readlines()
    with open(trips_file_path_generated, 'w') as file_generated:
        file_generated.write(header)
        #For each line, check if the trip_id is relevant and write the line in the new file if so
        for line in lines:
            line_split=line.strip().split(",")
            trip_id=line_split[trip_id_index]
            if trip_id in relevant_trips:
                file_generated.write(line)

# Create stops_times.txt file
# We need to keep stops only stop_times if they are used by the relevant trips
stop_times_file_path=os.path.join(gtfs_folder_old,"stop_times.txt")
stop_times_file_path_generated=os.path.join(gtfs_folder_generated,"stop_times.txt")
relevant_stops=[]
with open(stop_times_file_path, 'r') as file:
    #Read the header
    header=file.readline()
    #Find at which position the trip_id and stop_id are
    header_split=header.strip().split(",")
    trip_id_index=header_split.index("trip_id")
    stop_id_index=header_split.index("stop_id")
    #Read all remaining lines
    lines=file.readlines()
    with open(stop_times_file_path_generated, 'w') as file_generated:
        file_generated.write(header)
        #For each line, check if the trip_id is relevant and write the line in the new file if so
        for line in lines:
            line_split=line.strip().split(",")
            trip_id=line_split[trip_id_index]
            if trip_id in relevant_trips:
                file_generated.write(line)
                stop_id=line_split[stop_id_index]
                relevant_stops.append(stop_id)
relevant_stops = list(set(relevant_stops))

# Some stops appear in the cap file but not in the stop_times file. We need to add them to the stops.txt file
# the stop_times file format is: trip_id,arrival_time,departure_time,stop_id,stop_sequence,pickup_type,drop_off_type
# For all lines in the generated cap file, we need to find the departure stop_id and the arrival stop_id and add them to the stops.txt file if it is not already there
# The stop_times file is already generated so we can use it to find the relevant stops
# The stop_times file is sorted by trip id and arrival time at stops. We have to insert the stops in the right order in the stop_times.txt file. 
# Moreover when needed the sequence will need to be updated in the stop_times.txt file.

#Get all stop times from the stop_times file in a dictionary of lists of stops for each trip_id:
stop_times_dict=defaultdict(list)
with open(stop_times_file_path_generated, 'r') as file:
    #Read the header
    header=file.readline()
    #Find at which position the trip_id and stop_id are
    header_split=header.strip().split(",")
    trip_id_index=header_split.index("trip_id")
    arrival_time_index=header_split.index("arrival_time")
    departure_time_index=header_split.index("departure_time")
    stop_id_index=header_split.index("stop_id")
    stop_sequence_index=header_split.index("stop_sequence")
    #pickup and dropoff are always 0

    #Read all remaining lines
    lines=file.readlines()
    #For each line, check if the trip_id is relevant and write the line in the new file if so
    for line in lines:
        line_split=line.strip().split(",")
        trip_id=line_split[trip_id_index]
        arrival_time=line_split[arrival_time_index]
        departure_time=line_split[departure_time_index]
        stop_id=line_split[stop_id_index]
        stop_sequence=line_split[stop_sequence_index]
        if trip_id in stop_times_dict:
            stop_times_dict[trip_id].append([arrival_time,departure_time,stop_id,stop_sequence])
        else:
            stop_times_dict[trip_id]=[[arrival_time,departure_time,stop_id,stop_sequence],]
add_stops=[]
with open(cap_file_path_generated, 'r') as file:
    # Read the header
    header_cap=file.readline()
    # Find at which position the stop_id is
    header_split=header_cap.strip().split(";")
    trip_id_index=header_split.index("S_VEHJOBID_IDJOURNALIER")
    origin_stop_id_index=header_split.index("L_CHRONOBUS")
    origin_stop_name_index=header_split.index("L_CHRONOBUS_DESCRIPTION")
    origin_stop_lat_index=header_split.index("L_LAT_ARRET")
    origin_stop_lon_index=header_split.index("L_LON_ARRET")
    departure_time_at_origin_index=header_split.index("S_H_DEP_REEL28")

    destination_stop_id_index=header_split.index("D_CHRONOBUS_DESC")
    destination_stop_name_index=header_split.index("D_CHRONOBUS_DESCRIPTION_DESC")
    destination_stop_lat_index=header_split.index("D_LAT_STOP_DESC")
    destination_stop_lon_index=header_split.index("D_LON_STOP_DESC")
    arrival_time_at_destination_index=header_split.index("D_H_ARR_REEL28_DESC")
    
    # Read all remaining lines
    lines=file.readlines()
    # For each line, check if the stop_id is relevant and write the line in the new file if so
    for line in lines:
        line_split=line.strip().split(";")
        trip_id=line_split[trip_id_index]
        origin_stop_id=line_split[origin_stop_id_index]
        destination_stop_id=line_split[destination_stop_id_index]
        if origin_stop_id not in [stop_info[2] for stop_info in stop_times_dict[trip_id]]:
            if (origin_stop_id=='' or origin_stop_id==' ' or line_split[departure_time_at_origin_index]=='' or line_split[departure_time_at_origin_index]==' ')==False: #stop_id is empty
                line_split[departure_time_at_origin_index]
                stop_times_dict[trip_id].append([line_split[departure_time_at_origin_index],
                                                line_split[departure_time_at_origin_index],
                                                origin_stop_id,
                                                -1])
                add_stops.append([trip_id,
                                origin_stop_id,
                                line_split[origin_stop_name_index],
                                line_split[origin_stop_lat_index],
                                line_split[origin_stop_lon_index],
                                line_split[departure_time_at_origin_index]])
        if destination_stop_id not in [stop_info[2] for stop_info in stop_times_dict[trip_id]]:
            if (destination_stop_id=='' or destination_stop_id==' ' or line_split[arrival_time_at_destination_index]=='' or line_split[arrival_time_at_destination_index]==' ')==False: #stop_id is empty
                relevant_stops.append(destination_stop_id)
                stop_times_dict[trip_id].append([line_split[arrival_time_at_destination_index],
                                                line_split[arrival_time_at_destination_index],
                                                destination_stop_id,
                                                -1])
                add_stops.append([trip_id,
                                destination_stop_id,
                                line_split[destination_stop_name_index],
                                line_split[destination_stop_lat_index],
                                line_split[destination_stop_lon_index],
                                line_split[arrival_time_at_destination_index]])
relevant_stops = list(set(relevant_stops))

#Sort the stops by trip_id and arrival time
for trip_id in stop_times_dict:
    stop_times_dict[trip_id]=sorted(stop_times_dict[trip_id], key=itemgetter(0))
    prev=0
    stop_times=stop_times_dict[trip_id]
    for i in range(len(stop_times)):
        sequence=int(stop_times[i][3])
        if sequence==-1:
            sequence=prev+1
        elif sequence==prev:
            sequence+=1
        stop_times[i][3]=str(sequence)
        prev=sequence
    stop_times_dict[trip_id]=stop_times

#Rewrite the stop_times file
with open(stop_times_file_path_generated, 'w') as file:
    file.write(header)
    for trip_id in stop_times_dict:
        for stop_info in stop_times_dict[trip_id]:
            file.write(trip_id+","+stop_info[0]+","+stop_info[1]+","+stop_info[2]+","+str(stop_info[3])+",0,0\n")

# Create stops.txt file
stops_file_path=os.path.join(gtfs_folder_old,"stops.txt")
stops_file_path_generated=os.path.join(gtfs_folder_generated,"stops.txt")
with open(stops_file_path, 'r') as file:
    #Read the header
    header=file.readline()
    #Find at which position the stop_id is
    header_split=header.strip().split(",")
    stop_id_index=header_split.index("stop_id")
    #Read all remaining lines
    lines=file.readlines()
    with open(stops_file_path_generated, 'w') as file_generated:
        file_generated.write(header)
        #For each line, check if the stop_id is relevant and write the line in the new file if so
        for line in lines:
            line_split=line.strip().split(",")
            stop_id=line_split[stop_id_index]
            if stop_id in relevant_stops:
                file_generated.write(line)
                relevant_stops.remove(stop_id)

#Add the stops that are not in the stops.txt file

if len(relevant_stops)>0:
    #List of all stops in stops.txt file
    stops_in_stops_file=[]
    with open(stops_file_path_generated, 'r') as file:
        #Read the header
        header=file.readline()
        #Find at which position the stop_id is
        header_split=header.strip().split(",")
        stop_id_index=header_split.index("stop_id")
        stop_name_index=header_split.index("stop_name")
        stop_lat_index=header_split.index("stop_lat")
        stop_lon_index=header_split.index("stop_lon")
        #Read all remaining lines
        lines=file.readlines()
        for line in lines:
            line_split=line.strip().split(",")
            stop_id=line_split[stop_id_index]
            stop_name=line_split[stop_name_index]
            stop_lat=line_split[stop_lat_index]
            stop_lon=line_split[stop_lon_index]
            stops_in_stops_file.append([stop_id,stop_name,stop_lat,stop_lon])
    add_stops=sorted(add_stops, key=itemgetter(1)) # sort by stop_id
    for info in add_stops:
        if info[1] in relevant_stops:
            relevant_stops.remove(info[1])
            if info[1]=='' or info[1]==' ': #stop_id is empty
                continue
            stops_in_stops_file.append([info[1],info[2],info[3],info[4]])
    stops_in_stops_file=sorted(stops_in_stops_file, key=itemgetter(0)) # sort by stop_id
    with open(stops_file_path_generated, 'w') as file:
        file.write(header)
        for stop_info in stops_in_stops_file:
            file.write(stop_info[0]+","+stop_info[1]+","+stop_info[2]+","+stop_info[3]+"\n")

#Generate a requests file and an available_connections file
logging.getLogger().setLevel(logging.DEBUG)

logger.info("Generating requests and available connections for a small instance of: November 1st 2019")
requests_savepath=os.path.join(gtfs_folder_generated,"requests.csv")
connections_savepath=os.path.join(gtfs_folder_generated,"available_connections.json")

parser = argparse.ArgumentParser()
parser.add_argument("--cap", help="path to the file containing CAP "
                                        "data.")
parser.add_argument("-s", "--stoptimes", help="path to the file containing"
                                            " the GTFS stop times.")
parser.add_argument("-r", "--requests", help="path to output file that "
                                            "will contain the requests.")
parser.add_argument("-c", "--connections", help="path to output file that "
                                                "will contain the "
                                                "available connections.")
args = parser.parse_args(["--cap",cap_file_path_generated,"-s",stop_times_file_path_generated,"-r",requests_savepath,"-c",connections_savepath])

# CAPRequestsGenerator
logger.info("CAPRequestsGenerator")
stl_cap_requests_generator = CAPRequestsGenerator(args.cap, args.stoptimes)

requests_df = stl_cap_requests_generator.generate_requests(max_connection_time=5400,
                    release_time_delta=600, ready_time_delta=60,
                    due_time_delta=3600)

# Save to file
stl_cap_requests_generator.save_to_csv(args.requests)

# AvailableConnectionsExtractor
logger.info("AvailableConnectionsExtractor ")
available_connections_extractor =AvailableConnectionsExtractor(args.cap, args.stoptimes)

available_connections = available_connections_extractor.extract_available_connections(max_distance)

# # Save to file
available_connections_extractor.save_to_json(args.connections)
logger.info("Done extracting available connections for generated instance.")