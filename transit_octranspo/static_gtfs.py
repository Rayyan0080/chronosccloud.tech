"""
Static GTFS (General Transit Feed Specification) parser for OC Transpo.

Loads GTFS zip file, parses stops.txt and routes.txt, and stores in MongoDB.
This is OPTIONAL - system works without it.
"""

import csv
import logging
import os
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Any
import io

logger = logging.getLogger(__name__)

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    from pathlib import Path as PathLib
    env_path = PathLib(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed, skip

# Add project root to path for agents.shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_gtfs_zip_path() -> Optional[str]:
    """
    Get path to GTFS zip file from environment variable.
    
    Returns:
        Path to GTFS zip file or None if not set
    """
    return os.getenv("OCTRANSPO_GTFS_ZIP_PATH")


def is_gtfs_available() -> bool:
    """
    Check if GTFS zip file is available.
    
    Returns:
        True if GTFS zip path is set and file exists, False otherwise
    """
    zip_path = get_gtfs_zip_path()
    if not zip_path:
        return False
    
    return os.path.exists(zip_path) and os.path.isfile(zip_path)


def parse_gtfs_stops(gtfs_zip_path: str) -> List[Dict[str, Any]]:
    """
    Parse stops.txt from GTFS zip file.
    
    Args:
        gtfs_zip_path: Path to GTFS zip file
        
    Returns:
        List of stop dictionaries with stop_id, name, lat, lon
    """
    stops = []
    
    try:
        with zipfile.ZipFile(gtfs_zip_path, 'r') as zip_ref:
            if 'stops.txt' not in zip_ref.namelist():
                logger.warning("stops.txt not found in GTFS zip file")
                return stops
            
            # Read stops.txt from zip
            with zip_ref.open('stops.txt') as stops_file:
                # Handle BOM and encoding
                content = stops_file.read()
                if content.startswith(b'\xef\xbb\xbf'):
                    content = content[3:]  # Remove BOM
                
                text_content = content.decode('utf-8-sig')
                reader = csv.DictReader(io.StringIO(text_content))
                
                for row in reader:
                    try:
                        stop_id = row.get('stop_id', '').strip()
                        stop_name = row.get('stop_name', '').strip()
                        stop_lat = row.get('stop_lat', '').strip()
                        stop_lon = row.get('stop_lon', '').strip()
                        
                        if not stop_id or not stop_lat or not stop_lon:
                            continue
                        
                        stops.append({
                            'stop_id': stop_id,
                            'name': stop_name or stop_id,
                            'lat': float(stop_lat),
                            'lon': float(stop_lon),
                        })
                    except (ValueError, KeyError) as e:
                        logger.debug(f"Skipping invalid stop row: {e}")
                        continue
        
        logger.info(f"Parsed {len(stops)} stops from GTFS zip")
        return stops
        
    except zipfile.BadZipFile:
        logger.error(f"Invalid zip file: {gtfs_zip_path}")
        return []
    except Exception as e:
        logger.error(f"Error parsing stops.txt: {e}", exc_info=True)
        return []


def parse_gtfs_routes(gtfs_zip_path: str) -> List[Dict[str, Any]]:
    """
    Parse routes.txt from GTFS zip file.
    
    Args:
        gtfs_zip_path: Path to GTFS zip file
        
    Returns:
        List of route dictionaries with route_id, short_name, long_name
    """
    routes = []
    
    try:
        with zipfile.ZipFile(gtfs_zip_path, 'r') as zip_ref:
            if 'routes.txt' not in zip_ref.namelist():
                logger.warning("routes.txt not found in GTFS zip file")
                return routes
            
            # Read routes.txt from zip
            with zip_ref.open('routes.txt') as routes_file:
                # Handle BOM and encoding
                content = routes_file.read()
                if content.startswith(b'\xef\xbb\xbf'):
                    content = content[3:]  # Remove BOM
                
                text_content = content.decode('utf-8-sig')
                reader = csv.DictReader(io.StringIO(text_content))
                
                for row in reader:
                    try:
                        route_id = row.get('route_id', '').strip()
                        route_short_name = row.get('route_short_name', '').strip()
                        route_long_name = row.get('route_long_name', '').strip()
                        
                        if not route_id:
                            continue
                        
                        routes.append({
                            'route_id': route_id,
                            'short_name': route_short_name or route_id,
                            'long_name': route_long_name or route_short_name or route_id,
                        })
                    except (ValueError, KeyError) as e:
                        logger.debug(f"Skipping invalid route row: {e}")
                        continue
        
        logger.info(f"Parsed {len(routes)} routes from GTFS zip")
        return routes
        
    except zipfile.BadZipFile:
        logger.error(f"Invalid zip file: {gtfs_zip_path}")
        return []
    except Exception as e:
        logger.error(f"Error parsing routes.txt: {e}", exc_info=True)
        return []


def load_gtfs_to_mongodb(gtfs_zip_path: Optional[str] = None) -> bool:
    """
    Load GTFS data from zip file into MongoDB.
    
    Args:
        gtfs_zip_path: Optional path to GTFS zip file. If None, uses environment variable.
        
    Returns:
        True if successful, False otherwise
    """
    if not gtfs_zip_path:
        gtfs_zip_path = get_gtfs_zip_path()
    
    if not gtfs_zip_path or not os.path.exists(gtfs_zip_path):
        logger.warning("GTFS zip file not provided or not found. Static GTFS data unavailable.")
        return False
    
    try:
        from pymongo import MongoClient
        from agents.shared.config import get_mongodb_config
        
        # Get MongoDB config
        config = get_mongodb_config()
        
        # Build connection string
        if config["username"] and config["password"]:
            connection_string = (
                f"mongodb://{config['username']}:{config['password']}"
                f"@{config['host']}:{config['port']}/{config['database']}"
                f"?authSource=admin"
            )
        else:
            connection_string = (
                f"mongodb://{config['host']}:{config['port']}/{config['database']}"
            )
        
        # Connect to MongoDB
        client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
        db = client[config["database"]]
        
        # Parse GTFS data
        logger.info(f"Loading GTFS data from {gtfs_zip_path}...")
        stops = parse_gtfs_stops(gtfs_zip_path)
        routes = parse_gtfs_routes(gtfs_zip_path)
        
        if not stops and not routes:
            logger.warning("No GTFS data parsed from zip file")
            client.close()
            return False
        
        # Store stops in MongoDB
        if stops:
            stops_collection = db['transit_stops']
            stops_collection.delete_many({})  # Clear existing data
            stops_collection.insert_many(stops)
            
            # Create indexes
            stops_collection.create_index('stop_id', unique=True)
            stops_collection.create_index([('lat', 1), ('lon', 1)])  # Geospatial index
            
            logger.info(f"Stored {len(stops)} stops in MongoDB")
        
        # Store routes in MongoDB
        if routes:
            routes_collection = db['transit_routes']
            routes_collection.delete_many({})  # Clear existing data
            routes_collection.insert_many(routes)
            
            # Create indexes
            routes_collection.create_index('route_id', unique=True)
            
            logger.info(f"Stored {len(routes)} routes in MongoDB")
        
        client.close()
        logger.info("GTFS data loaded successfully into MongoDB")
        return True
        
    except ImportError:
        logger.error("pymongo not installed. Install with: pip install pymongo")
        return False
    except Exception as e:
        logger.error(f"Error loading GTFS to MongoDB: {e}", exc_info=True)
        return False


def get_stop_info(stop_id: str) -> Optional[Dict[str, Any]]:
    """
    Get stop information from MongoDB.
    
    Args:
        stop_id: Stop ID to look up
        
    Returns:
        Stop dictionary or None if not found
    """
    try:
        from pymongo import MongoClient
        from agents.shared.config import get_mongodb_config
        
        config = get_mongodb_config()
        
        if config["username"] and config["password"]:
            connection_string = (
                f"mongodb://{config['username']}:{config['password']}"
                f"@{config['host']}:{config['port']}/{config['database']}"
                f"?authSource=admin"
            )
        else:
            connection_string = (
                f"mongodb://{config['host']}:{config['port']}/{config['database']}"
            )
        
        client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
        db = client[config["database"]]
        stops_collection = db['transit_stops']
        
        stop = stops_collection.find_one({'stop_id': stop_id})
        client.close()
        
        return stop
        
    except Exception as e:
        logger.debug(f"Error getting stop info: {e}")
        return None


def get_route_info(route_id: str) -> Optional[Dict[str, Any]]:
    """
    Get route information from MongoDB.
    
    Args:
        route_id: Route ID to look up
        
    Returns:
        Route dictionary or None if not found
    """
    try:
        from pymongo import MongoClient
        from agents.shared.config import get_mongodb_config
        
        config = get_mongodb_config()
        
        if config["username"] and config["password"]:
            connection_string = (
                f"mongodb://{config['username']}:{config['password']}"
                f"@{config['host']}:{config['port']}/{config['database']}"
                f"?authSource=admin"
            )
        else:
            connection_string = (
                f"mongodb://{config['host']}:{config['port']}/{config['database']}"
            )
        
        client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
        db = client[config["database"]]
        routes_collection = db['transit_routes']
        
        route = routes_collection.find_one({'route_id': route_id})
        client.close()
        
        return route
        
    except Exception as e:
        logger.debug(f"Error getting route info: {e}")
        return None


if __name__ == "__main__":
    # Command-line usage
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1:
        zip_path = sys.argv[1]
    else:
        zip_path = get_gtfs_zip_path()
    
    if zip_path:
        success = load_gtfs_to_mongodb(zip_path)
        sys.exit(0 if success else 1)
    else:
        logger.error("No GTFS zip path provided. Set OCTRANSPO_GTFS_ZIP_PATH or provide as argument.")
        sys.exit(1)

