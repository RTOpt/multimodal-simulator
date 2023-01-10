import argparse
import logging

from multimodalsim.reader.available_connections_extractor import \
    AvailableConnectionsExtractor
from multimodalsim.reader.requests_generator import CAPRequestsGenerator

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)

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
    # Example: -c ../../data/fixed_line/stl/available_connections/available_connections_0p5.json
    args = parser.parse_args()

    # CAPRequestsGenerator
    logger.info("CAPRequestsGenerator")
    stl_cap_requests_generator = CAPRequestsGenerator(args.cap, args.stoptimes)

    requests_df = stl_cap_requests_generator.generate_requests()

    # Save to file
    stl_cap_requests_generator.save_to_csv(args.requests)
    requests_sample_file_path = "../../data/fixed_line/stl/requests/" \
                                "stl_requests_100.csv"
    stl_cap_requests_generator.save_to_csv(requests_sample_file_path,
                                           requests_df.sample(100))

    # AvailableConnectionsExtractor
    logger.info("AvailableConnectionsExtractor")
    available_connections_extractor = \
        AvailableConnectionsExtractor(args.cap, args.stoptimes)

    max_distance = 0.5
    available_connections = \
        available_connections_extractor.extract_available_connections(
            max_distance)

    # Save to file
    # available_connections_extractor.save_to_json(args.connections)
