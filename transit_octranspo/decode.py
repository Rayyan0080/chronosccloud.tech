"""
GTFS-RT protobuf decoding utilities.

Decodes Google Transit GTFS-RT protobuf messages into Python dictionaries and models.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

try:
    from google.transit import gtfs_realtime_pb2
    PROTOBUF_AVAILABLE = True
except ImportError:
    try:
        # Alternative import path
        import gtfs_realtime_pb2
        PROTOBUF_AVAILABLE = True
    except ImportError:
        PROTOBUF_AVAILABLE = False
        logger.warning(
            "gtfs-realtime-bindings library not installed. Install with: pip install gtfs-realtime-bindings"
        )


def decode_feed_message(feed_data: bytes) -> Dict[str, Any]:
    """
    Decode GTFS-RT FeedMessage protobuf into Python dictionary.
    
    Args:
        feed_data: Raw protobuf bytes from GTFS-RT feed
        
    Returns:
        Dictionary containing decoded feed message
        
    Raises:
        ImportError: If protobuf library is not available
        ValueError: If feed data cannot be decoded
    """
    if not PROTOBUF_AVAILABLE:
        raise ImportError(
            "google-transit-feed library required. Install with: pip install gtfs-realtime-bindings"
        )
    
    try:
        feed_message = gtfs_realtime_pb2.FeedMessage()
        feed_message.ParseFromString(feed_data)
        
        return {
            "header": {
                "gtfs_realtime_version": feed_message.header.gtfs_realtime_version,
                "incrementality": feed_message.header.incrementality,
                "timestamp": feed_message.header.timestamp,
            },
            "entity": [decode_entity(entity) for entity in feed_message.entity],
        }
    except Exception as e:
        logger.error(f"Failed to decode GTFS-RT feed: {e}")
        raise ValueError(f"Invalid GTFS-RT feed data: {e}") from e


def decode_entity(entity) -> Dict[str, Any]:
    """
    Decode a FeedEntity from GTFS-RT protobuf.
    
    Args:
        entity: FeedEntity protobuf object
        
    Returns:
        Dictionary containing decoded entity
    """
    result = {
        "id": entity.id,
        "is_deleted": entity.is_deleted,
    }
    
    if entity.HasField("vehicle"):
        result["vehicle"] = decode_vehicle_position(entity.vehicle)
    
    if entity.HasField("trip_update"):
        result["trip_update"] = decode_trip_update(entity.trip_update)
    
    if entity.HasField("alert"):
        result["alert"] = decode_alert(entity.alert)
    
    return result


def decode_vehicle_position(vehicle) -> Dict[str, Any]:
    """
    Decode VehiclePosition from GTFS-RT protobuf.
    
    Args:
        vehicle: VehiclePosition protobuf object
        
    Returns:
        Dictionary containing decoded vehicle position
    """
    result = {}
    
    if vehicle.HasField("trip"):
        trip = vehicle.trip
        result["trip"] = {
            "trip_id": trip.trip_id if trip.HasField("trip_id") else None,
            "route_id": trip.route_id if trip.HasField("route_id") else None,
        }
    
    if vehicle.HasField("vehicle"):
        veh = vehicle.vehicle
        result["vehicle"] = {
            "id": veh.id if veh.HasField("id") else None,
            "label": veh.label if veh.HasField("label") else None,
            "license_plate": veh.license_plate if veh.HasField("license_plate") else None,
        }
    
    if vehicle.HasField("position"):
        pos = vehicle.position
        result["position"] = {
            "latitude": pos.latitude,
            "longitude": pos.longitude,
            "bearing": pos.bearing if pos.HasField("bearing") else None,
            "speed": pos.speed if pos.HasField("speed") else None,
        }
    
    if vehicle.HasField("current_stop_sequence"):
        result["current_stop_sequence"] = vehicle.current_stop_sequence
    
    if vehicle.HasField("current_status"):
        result["current_status"] = vehicle.current_status
    
    if vehicle.HasField("occupancy_status"):
        result["occupancy_status"] = vehicle.occupancy_status
    
    if vehicle.HasField("timestamp"):
        result["timestamp"] = datetime.fromtimestamp(vehicle.timestamp, tz=None)
    
    return result


def decode_trip_update(trip_update) -> Dict[str, Any]:
    """
    Decode TripUpdate from GTFS-RT protobuf.
    
    Args:
        trip_update: TripUpdate protobuf object
        
    Returns:
        Dictionary containing decoded trip update
    """
    result = {}
    
    if trip_update.HasField("trip"):
        trip = trip_update.trip
        result["trip"] = {
            "trip_id": trip.trip_id if trip.HasField("trip_id") else None,
            "route_id": trip.route_id if trip.HasField("route_id") else None,
        }
    
    if trip_update.HasField("vehicle"):
        veh = trip_update.vehicle
        result["vehicle"] = {
            "id": veh.id if veh.HasField("id") else None,
            "label": veh.label if veh.HasField("label") else None,
        }
    
    if trip_update.stop_time_update:
        result["stop_time_update"] = [
            decode_stop_time_update(stu) for stu in trip_update.stop_time_update
        ]
    
    if trip_update.HasField("delay"):
        result["delay"] = trip_update.delay
    
    if trip_update.HasField("timestamp"):
        result["timestamp"] = datetime.fromtimestamp(trip_update.timestamp, tz=None)
    
    return result


def decode_stop_time_update(stu) -> Dict[str, Any]:
    """
    Decode StopTimeUpdate from GTFS-RT protobuf.
    
    Args:
        stu: StopTimeUpdate protobuf object
        
    Returns:
        Dictionary containing decoded stop time update
    """
    result = {}
    
    if stu.HasField("stop_sequence"):
        result["stop_sequence"] = stu.stop_sequence
    
    if stu.HasField("stop_id"):
        result["stop_id"] = stu.stop_id
    
    if stu.HasField("arrival"):
        arr = stu.arrival
        result["arrival"] = {
            "time": datetime.fromtimestamp(arr.time, tz=None) if arr.HasField("time") else None,
            "delay": arr.delay if arr.HasField("delay") else None,
        }
    
    if stu.HasField("departure"):
        dep = stu.departure
        result["departure"] = {
            "time": datetime.fromtimestamp(dep.time, tz=None) if dep.HasField("time") else None,
            "delay": dep.delay if dep.HasField("delay") else None,
        }
    
    return result


def decode_alert(alert) -> Dict[str, Any]:
    """
    Decode Alert from GTFS-RT protobuf.
    
    Args:
        alert: Alert protobuf object
        
    Returns:
        Dictionary containing decoded alert
    """
    result = {}
    
    if alert.active_period:
        result["active_period"] = [
            {
                "start": datetime.fromtimestamp(ap.start, tz=None) if ap.HasField("start") else None,
                "end": datetime.fromtimestamp(ap.end, tz=None) if ap.HasField("end") else None,
            }
            for ap in alert.active_period
        ]
    
    if alert.informed_entity:
        result["informed_entity"] = [
            {
                "agency_id": ie.agency_id if ie.HasField("agency_id") else None,
                "route_id": ie.route_id if ie.HasField("route_id") else None,
                "trip": {
                    "trip_id": ie.trip.trip_id if ie.HasField("trip") and ie.trip.HasField("trip_id") else None,
                    "route_id": ie.trip.route_id if ie.HasField("trip") and ie.trip.HasField("route_id") else None,
                } if ie.HasField("trip") else None,
                "stop_id": ie.stop_id if ie.HasField("stop_id") else None,
            }
            for ie in alert.informed_entity
        ]
    
    if alert.header_text:
        result["header_text"] = [
            {"text": ht.text, "language": ht.language if ht.HasField("language") else None}
            for ht in alert.header_text.translation
        ]
    
    if alert.description_text:
        result["description_text"] = [
            {"text": dt.text, "language": dt.language if dt.HasField("language") else None}
            for dt in alert.description_text.translation
        ]
    
    return result

