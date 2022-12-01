import numpy as np
from pathlib import Path
import os
from operator import itemgetter
import logging

logger = logging.getLogger(__name__)

class GTFSGenerator:
    def __init__(self, gtfs_folder):
        self.__gtfs_folder = gtfs_folder
        if not os.path.exists(self.__gtfs_folder):
            os.makedirs(self.__gtfs_folder)

    def build_trips(self, filename, path_to_file):
        name = os.path.join(path_to_file, filename)
        alltype = np.dtype(
            [('f0', 'U12'), ('f1', 'U12'), ('f2', 'U12'), ('f3', 'U12'),
             ('f4', 'U12')])
        data_trips = np.genfromtxt(name, delimiter=",", dtype=alltype,
                                   # usecols=['P_LIGNE','P_DIR_NSEO','_SEM_SAM_DIM','P_TYPE_IMPRIME'],
                                   #     usecols=[131, 133, 222, 178, 214],
                                   usecols=[131, 133, 222, 96, 214],
                                   names=True)
        # 0-numero de ligne devient 131-AVJ_LIGNE
        # 1-direction en format N/S/E/O devient 133-AVJ_DIR_NSEO
        # 2-jour de la semaine devient 222-AC_SEM_SAM_DIM
        # OLD 3-identifiant du voyage devient 178 AVO_VEHJOBID
        # 3-identifiant du voyage devient 96 AAJ_ID_VAL_VOYAGE
        # 4-214-AC_DT_TRAITEE-date
        data_trips = np.unique(data_trips)
        data_trips = filter(self.__filter_function_trips, data_trips)
        data_trips = sorted(data_trips, key=itemgetter(4, 0, 1))
        dates = []
        for x in data_trips:
            dates.append(x[4][0:10])
        dates = np.unique(dates)
        names = []
        i = 0
        n = len(data_trips)
        for date in dates:
            completename = os.path.join(self.__gtfs_folder, "trips_"
                                        + date[0:4] + date[5:7] + date[8:10]
                                        + ".txt")
            names.append(completename)
            my_file = Path(completename)
            if my_file.is_file() == False:  # le fichier n'existe pas
                f = open(completename, "w")
                f.write(
                    "route_id,service_id,trip_id,shape_id,trip_short_name\n")
                x = data_trips[i]
                val = x[4][0:10]
                while val == date:
                    f.write(
                        str(x[0]) + str(x[1]) + ',' + str(x[2]) + ',' + str(
                            x[3]) + ',' + str(x[0]) + str(x[1]) + ',' + str(
                            x[0]) + '\n')
                    i += 1
                    if i < n:
                        x = data_trips[i]
                        val = x[4][0:10]
                    else:
                        val = 'haha'
                f.close()
            else:  # le fichier existe deja
                alltype = (
                    [('f0', 'U12'), ('f1', 'U12'), ('f2', 'U12'),
                     ('f3', 'U12'),
                     ('f4', 'U12')])
                trips = np.genfromtxt(completename, delimiter=",",
                                      dtype=alltype, names=True)
                trips = np.array(trips, dtype=object)
                x = data_trips[i]
                val = x[4][0:10]
                while val == date:
                    np.append(trips, (
                        str(x[1]) + str(x[0]), str(x[2]), str(x[3]),
                        str(x[0]) + str(x[1]), str(x[0])))
                    i += 1
                    if i < n:
                        x = data_trips[i]
                        val = x[4][0:10]
                    else:
                        val = 'haha'
                trips = list(np.unique(trips))
                trips = sorted(trips, key=itemgetter(0))
                f = open(completename, "w")
                f.write(
                    "route_id,service_id,trip_id,shape_id,trip_short_name\n")
                for x in trips:
                    f.write(
                        x[0] + ',' + x[1] + ',' + x[2] + ',' + x[3] + ',' + x[
                            4] + '\n')
                f.close()
        return names

    def build_stop_times(self, filename, path_to_file):
        name = os.path.join(path_to_file, filename)
        # 0-id de l'arret-devient 64-AL_CHRONOBUS
        # 1-longitude de l'arret-devient 67-AL_WGS84COORDX
        # 2-latitude de l'arret-devient 68-AL_WGS84COORDY
        # 3-heure d'arrivee reelle a l'arret format secondes depuis minuit devient 109-AAO_H_ARR_REEL28
        # 4-heure de depart reelle depuis l'arret format secondes depuis minuit devient 110-AAO_H_DEP_REEL28
        # 5-sequence de l'arret pour ce voyage devient 89-AL_SEQ2
        # 6-distance cumulee depuis l'origine devient 66-AL_DISTCUMULKM
        # 7-ligne devient 188-AVO_LIGNE
        # 8-direction devient 133-AVJ_DIR_NSEO
        # OLD 9-trip id devient 178-AVO_VEHJOBID
        # 9-trip id devient 96-AAJ_ID_VAL_VOYAGE
        # 10-214-AC_DT_TRAITEE-date
        alltype = alltype = (
        [('f0', 'U12'), ('f1', 'U12'), ('f2', 'U12'), ('f3', 'U12'),
         ('f4', 'U12'), ('f5', 'U12'), ('f6', 'U12'), ('f7', 'U12'),
         ('f8', 'U12'), ('f9', 'U12'), ('f10', 'U12')])
        data_stop_times = np.genfromtxt(name, delimiter=",", dtype=alltype,
                                        usecols=[64, 67, 68, 109, 110, 89, 66,
                                                 188, 133, 96, 214],
                                        names=True)
        data_stop_times = filter(self.__filter_function_stop_times,
                                 data_stop_times)
        tmp = []
        for x in data_stop_times:
            tmp.append((x[9], x[3], x[4], x[0], int(x[5]), x[6], x[10]))
        #         tmp.append((x[96],x[109],x[110], x[64], int(x[89]),x[66],x[214]))
        data_stop_times = sorted(tmp, key=itemgetter(6, 0, 4))
        dates = []
        for x in data_stop_times:
            dates.append(str(x[6][0:10]))
        dates = np.unique(dates)
        names = []
        i = 0
        n = len(data_stop_times)
        for date in dates:

            completename = os.path.join(self.__gtfs_folder, "stop_times_"
                                        + date[0:4] + date[5:7] + date[8:10]
                                        + ".txt")
            names.append(completename)
            my_file = Path(completename)
            if my_file.is_file() == False:
                # le fichier n'existe pas
                f = open(completename, "w")
                #             f.write("trip_id,arrival_time,departure_time,stop_id,stop_sequence,shape_dist_traveled\n")
                f.write(
                    "trip_id,arrival_time,departure_time,stop_id,stop_sequence,pickup_type,drop_off_type\n")
                x = data_stop_times[i]
                val = x[6][0:10]
                while val == date:
                    #                 arrival_time = datetime.datetime.fromtimestamp(int(x[1])).strftime('%H:%M:%S')
                    #                 departure_time = datetime.datetime.fromtimestamp(int(x[2])).strftime('%H:%M:%S')
                    arrival_time = str(x[1])
                    departure_time = str(x[2])
                    f.write(str(x[
                                    0]) + ',' + arrival_time + ',' + departure_time + ',' + str(
                        x[3]) + ',' + str(x[4]) + ',' + str(0) + ',' + str(
                        0) + '\n')
                    i += 1
                    if i < n:
                        x = data_stop_times[i]
                        val = x[6][0:10]
                    else:
                        val = 'haha'
                f.close()
            else:
                # le fichier existe, il faut les merger
                alltype = (
                [('f0', 'U12'), ('f1', 'U12'), ('f2', 'U12'), ('f3', 'U12'),
                 ('f4', 'i8'), ('f5', 'U12')])
                stop_times = np.genfromtxt(completename, delimiter=",",
                                           dtype=alltype, names=True)
                stop_times = np.array(stop_times, dtype=object)
                x = data_stop_times[i]

                val = x[6][0:10]
                while val == date:
                    #                 arrival_time = datetime.datetime.fromtimestamp(int(x[1])).strftime('%H:%M:%S')
                    #                 departure_time = datetime.datetime.fromtimestamp(int(x[2])).strftime('%H:%M:%S')
                    arrival_time = str(x[1])
                    departure_time = str(x[2])
                    np.append(stop_times, (
                    x[0], arrival_time, departure_time, x[3], int(x[4]), x[5]))
                    i += 1
                    if i < n:
                        x = data_stop_times[i]
                        val = x[6][0:10]
                    else:
                        val = 'haha'
                stop_times = list(np.unique(stop_times))
                stop_times = sorted(stop_times, key=itemgetter(0, 4))
                os.remove(completename)
                f = open(completename, "w")
                f.write(
                    "trip_id,arrival_time,departure_time,stop_id,stop_sequence,pickup_type,drop_off_type\n")
                for x in stop_times:
                    f.write(x[0] + ',' + x[1] + ',' + x[2] + ',' + x[
                        3] + ',' + str(x[4]) + ',' + str(0) + ',' + str(
                        0) + '\n')
                f.close()
        return names

    def __filter_function_trips(self, x):
        if x[3] == '':
            return False
        else:
            return True

    def __filter_function_stop_times(self, x):
        if x[9] == -1 or x[3] == '' or x[4] == '' or x[1] == '' or x[2] == '' \
                or x[5] == -1 or x[0] == -1:
            return False
        else:
            return True
