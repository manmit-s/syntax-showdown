import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import uuid
import json

# Global db instance
db = None

def initialize_firebase() -> None:
    """Initialize Firebase Admin SDK with credentials from Streamlit secrets."""
    global db
    try:
        if firebase_admin._apps:
            # Already initialized
            print("Firebase already initialized")
            db = firestore.client()
            return
        
        # Get credentials from secrets
        firebase_secrets = st.secrets.get("firebase_credentials")
        if not firebase_secrets:
            raise ValueError("firebase_credentials not found in Streamlit secrets")
        
        # Convert TOML dict to JSON string for credentials
        cred_dict = dict(firebase_secrets)
        
        # Create credentials object
        cred = credentials.Certificate(cred_dict)
        
        # Initialize Firebase
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("Firebase Firestore initialized successfully")
        
    except Exception as e:
        print(f"Failed to initialize Firebase: {e}")
        raise

def _get_db():
    """Get Firestore database instance, initializing if needed."""
    global db
    if db is None:
        initialize_firebase()
    return db

def generate_match_id() -> str:
    """Generate a unique match ID in format: clash_xxxxxx."""
    random_chars = uuid.uuid4().hex[:6]
    return f"clash_{random_chars}"

def create_match(problem_data: dict) -> str:
    """
    Create a new match document in Firestore.
    
    Args:
        problem_data: Dictionary with problem data from generate_problem()
    
    Returns:
        match_id: Unique ID for the created match
    """
    db = _get_db()
    
    match_id = generate_match_id()
    created_at = datetime.utcnow().isoformat() + "Z"
    
    match_data = {
        "created_at": created_at,
        "status": "waiting",
        "problem_data": problem_data,
        "players": {
            "p1": {
                "code": "",
                "score": 0,
                "status": "joined"
            },
            "p2": {
                "code": "",
                "score": 0,
                "status": "waiting"
            }
        }
    }
    
    try:
        doc_ref = db.collection("matches").document(match_id)
        doc_ref.set(match_data)
        print(f"Match created: {match_id}")
        return match_id
    except Exception as e:
        print(f"Failed to create match: {e}")
        raise

def get_match_state(match_id: str) -> dict | None:
    """
    Get current state of a match.
    
    Args:
        match_id: Unique match ID
    
    Returns:
        Dictionary with match data or None if not found
    """
    db = _get_db()
    
    try:
        doc_ref = db.collection("matches").document(match_id)
        doc = doc_ref.get()
        
        if doc.exists:
            match_data = doc.to_dict()
            match_data["id"] = match_id  # Add ID to returned data
            return match_data
        else:
            print(f"Match not found: {match_id}")
            return None
    except Exception as e:
        print(f"Failed to get match state: {e}")
        raise

def update_player_state(match_id: str, player: str, updates: dict) -> None:
    """
    Update player-specific fields in a match.
    
    Args:
        match_id: Unique match ID
        player: Player identifier ("p1" or "p2")
        updates: Dictionary with fields to update
    """
    db = _get_db()
    
    if player not in ["p1", "p2"]:
        raise ValueError(f"Invalid player: {player}. Must be 'p1' or 'p2'")
    
    try:
        doc_ref = db.collection("matches").document(match_id)
        
        # Build update dictionary with nested field paths
        update_dict = {}
        for key, value in updates.items():
            field_path = f"players.{player}.{key}"
            update_dict[field_path] = value
        
        doc_ref.update(update_dict)
        print(f"Updated {player} state in match {match_id}: {updates}")
        
    except Exception as e:
        print(f"Failed to update player state: {e}")
        raise

def update_match_status(match_id: str, status: str) -> None:
    """
    Update match-level status field.
    
    Args:
        match_id: Unique match ID
        status: New status ("waiting", "active", "finished")
    """
    if status not in ["waiting", "active", "finished"]:
        raise ValueError(f"Invalid status: {status}. Must be 'waiting', 'active', or 'finished'")
    
    db = _get_db()
    
    try:
        doc_ref = db.collection("matches").document(match_id)
        doc_ref.update({"status": status})
        print(f"Updated match {match_id} status to: {status}")
        
    except Exception as e:
        print(f"Failed to update match status: {e}")
        raise

def join_match_as_p2(match_id: str) -> bool:
    """
    Join an existing match as player 2.
    
    Args:
        match_id: Unique match ID
    
    Returns:
        True if joined successfully, False if match is full or not found
    """
    db = _get_db()
    
    try:
        doc_ref = db.collection("matches").document(match_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return False
        
        match_data = doc.to_dict()
        
        # Check if p2 is still waiting
        if match_data.get("players", {}).get("p2", {}).get("status") == "waiting":
            # Update p2 status to joined
            update_dict = {
                f"players.p2.status": "joined"
            }
            doc_ref.update(update_dict)
            
            # Update match status to active
            update_match_status(match_id, "active")
            print(f"Player 2 joined match: {match_id}")
            return True
        else:
            print(f"Match {match_id} is full or p2 already joined")
            return False
            
    except Exception as e:
        print(f"Failed to join match as p2: {e}")
        return False

def get_player_in_match(match_id: str) -> str:
    """
    Determine which player slot is available/assigned for current session.
    
    Args:
        match_id: Unique match ID
    
    Returns:
        "p1", "p2", or raises error
    """
    try:
        match_data = get_match_state(match_id)
        if not match_data:
            raise ValueError(f"Match not found: {match_id}")
        
        # Check session state first
        player_id = st.session_state.get("player_id")
        if player_id in ["p1", "p2"]:
            return player_id
        
        # Determine available player
        p1_status = match_data.get("players", {}).get("p1", {}).get("status")
        p2_status = match_data.get("players", {}).get("p2", {}).get("status")
        
        # If p2 is waiting, assign current user as p2
        if p2_status == "waiting":
            st.session_state["player_id"] = "p2"
            join_match_as_p2(match_id)
            return "p2"
        elif p1_status == "joined" and p2_status == "joined":
            # Both players already joined, check if we have a session state
            if not player_id:
                raise ValueError("Match is full (both players already joined)")
            return player_id
        else:
            # Should not happen
            raise ValueError("Unexpected match state")
            
    except Exception as e:
        print(f"Failed to get player in match: {e}")
        raise

if __name__ == "__main__":
    # Test the module
    print("Firebase Database Client Module - Testing interface")
    print("initialize_firebase(): OK (requires secrets)")
    print("generate_match_id(): Returns clash_xxxxxx format")
    print("create_match(problem_data): Creates Firestore document, returns match_id")
    print("get_match_state(match_id): Returns match dict or None")
    print("update_player_state(match_id, player, updates): Updates player fields")
    print("update_match_status(match_id, status): Updates match status")
    print("join_match_as_p2(match_id): Joins match as player 2")
    print("get_player_in_match(match_id): Determines player role")
