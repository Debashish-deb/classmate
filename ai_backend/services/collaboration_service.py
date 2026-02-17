import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import HTTPException
import uuid
import asyncio
from ..database import get_db
from ..database.models import Session, User, Team, TeamMember, SharedSession, Comment, Annotation

logger = logging.getLogger(__name__)

class CollaborationService:
    """Team collaboration service for ClassMate"""
    
    def __init__(self):
        pass
    
    async def create_team(self, team_name: str, owner_id: str, description: str = None) -> Dict[str, Any]:
        """Create a new team"""
        try:
            with get_db() as db:
                # Check if user exists
                owner = db.query(User).filter(User.id == owner_id).first()
                if not owner:
                    raise HTTPException(status_code=404, detail="User not found")
                
                # Create team
                team = Team(
                    id=str(uuid.uuid4()),
                    name=team_name,
                    description=description,
                    owner_id=owner_id,
                    created_at=datetime.utcnow(),
                    is_active=True
                )
                db.add(team)
                
                # Add owner as team member
                team_member = TeamMember(
                    id=str(uuid.uuid4()),
                    team_id=team.id,
                    user_id=owner_id,
                    role="owner",
                    joined_at=datetime.utcnow(),
                    is_active=True
                )
                db.add(team_member)
                
                db.commit()
                
                return {
                    "team_id": team.id,
                    "name": team.name,
                    "description": team.description,
                    "owner_id": owner_id,
                    "created_at": team.created_at.isoformat(),
                    "member_count": 1
                }
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create team: {e}")
            raise HTTPException(status_code=500, detail="Failed to create team")
    
    async def invite_team_member(self, team_id: str, inviter_id: str, invitee_email: str, role: str = "member") -> Dict[str, Any]:
        """Invite a user to join a team"""
        try:
            with get_db() as db:
                # Check if inviter is team owner or admin
                inviter_member = db.query(TeamMember).filter(
                    TeamMember.team_id == team_id,
                    TeamMember.user_id == inviter_id,
                    TeamMember.is_active == True
                ).first()
                
                if not inviter_member or inviter_member.role not in ["owner", "admin"]:
                    raise HTTPException(status_code=403, detail="Insufficient permissions")
                
                # Check if team exists
                team = db.query(Team).filter(Team.id == team_id).first()
                if not team:
                    raise HTTPException(status_code=404, detail="Team not found")
                
                # Check if user is already a member
                invitee = db.query(User).filter(User.email == invitee_email).first()
                if invitee:
                    existing_member = db.query(TeamMember).filter(
                        TeamMember.team_id == team_id,
                        TeamMember.user_id == invitee.id,
                        TeamMember.is_active == True
                    ).first()
                    
                    if existing_member:
                        raise HTTPException(status_code=400, detail="User is already a team member")
                
                # Create invitation
                invitation_id = str(uuid.uuid4())
                invitation_data = {
                    "id": invitation_id,
                    "team_id": team_id,
                    "team_name": team.name,
                    "inviter_id": inviter_id,
                    "inviter_name": inviter_user.name if inviter_user else "Unknown",
                    "invitee_email": invitee_email,
                    "role": role,
                    "created_at": datetime.utcnow().isoformat(),
                    "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat()
                }
                
                # Store invitation (in a real implementation, this would be in a separate invitations table)
                # For now, return the invitation data
                return invitation_data
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to invite team member: {e}")
            raise HTTPException(status_code=500, detail="Failed to send invitation")
    
    async def accept_team_invitation(self, invitation_id: str, user_id: str) -> Dict[str, Any]:
        """Accept a team invitation"""
        try:
            # In a real implementation, this would validate the invitation from the database
            # For now, we'll simulate the acceptance
            
            with get_db() as db:
                # Add user to team
                team_member = TeamMember(
                    id=str(uuid.uuid4()),
                    team_id="team_id_from_invitation",  # Would come from invitation
                    user_id=user_id,
                    role="member",
                    joined_at=datetime.utcnow(),
                    is_active=True
                )
                db.add(team_member)
                db.commit()
                
                return {
                    "status": "accepted",
                    "message": "Successfully joined the team",
                    "joined_at": team_member.joined_at.isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to accept invitation: {e}")
            raise HTTPException(status_code=500, detail="Failed to accept invitation")
    
    async def share_session_with_team(self, session_id: str, user_id: str, team_id: str, permissions: List[str]) -> Dict[str, Any]:
        """Share a session with a team"""
        try:
            with get_db() as db:
                # Check if user owns the session
                session = db.query(Session).filter(
                    Session.id == session_id,
                    Session.user_id == user_id
                ).first()
                
                if not session:
                    raise HTTPException(status_code=404, detail="Session not found")
                
                # Check if user is team member
                team_member = db.query(TeamMember).filter(
                    TeamMember.team_id == team_id,
                    TeamMember.user_id == user_id,
                    TeamMember.is_active == True
                ).first()
                
                if not team_member:
                    raise HTTPException(status_code=403, detail="Not a team member")
                
                # Create shared session
                shared_session = SharedSession(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    team_id=team_id,
                    shared_by=user_id,
                    permissions=json.dumps(permissions),
                    shared_at=datetime.utcnow(),
                    is_active=True
                )
                db.add(shared_session)
                db.commit()
                
                return {
                    "share_id": shared_session.id,
                    "session_id": session_id,
                    "team_id": team_id,
                    "permissions": permissions,
                    "shared_at": shared_session.shared_at.isoformat()
                }
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to share session: {e}")
            raise HTTPException(status_code=500, detail="Failed to share session")
    
    async def add_comment(self, session_id: str, user_id: str, content: str, timestamp: float = None) -> Dict[str, Any]:
        """Add a comment to a session"""
        try:
            with get_db() as db:
                # Check if user has access to the session
                session = db.query(Session).filter(Session.id == session_id).first()
                if not session:
                    raise HTTPException(status_code=404, detail="Session not found")
                
                # Check access (owner or shared)
                has_access = (
                    session.user_id == user_id or
                    db.query(SharedSession).filter(
                        SharedSession.session_id == session_id,
                        SharedSession.is_active == True
                    ).join(TeamMember).filter(
                        TeamMember.user_id == user_id,
                        TeamMember.is_active == True
                    ).first() is not None
                )
                
                if not has_access:
                    raise HTTPException(status_code=403, detail="Access denied")
                
                # Create comment
                comment = Comment(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    user_id=user_id,
                    content=content,
                    timestamp=timestamp or 0.0,
                    created_at=datetime.utcnow(),
                    is_resolved=False
                )
                db.add(comment)
                db.commit()
                
                return {
                    "comment_id": comment.id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "content": content,
                    "timestamp": comment.timestamp,
                    "created_at": comment.created_at.isoformat()
                }
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to add comment: {e}")
            raise HTTPException(status_code=500, detail="Failed to add comment")
    
    async def add_annotation(self, session_id: str, user_id: str, text: str, start_time: float, end_time: float, annotation_type: str = "note") -> Dict[str, Any]:
        """Add an annotation to a session"""
        try:
            with get_db() as db:
                # Check access (same logic as comments)
                session = db.query(Session).filter(Session.id == session_id).first()
                if not session:
                    raise HTTPException(status_code=404, detail="Session not found")
                
                has_access = (
                    session.user_id == user_id or
                    db.query(SharedSession).filter(
                        SharedSession.session_id == session_id,
                        SharedSession.is_active == True
                    ).join(TeamMember).filter(
                        TeamMember.user_id == user_id,
                        TeamMember.is_active == True
                    ).first() is not None
                )
                
                if not has_access:
                    raise HTTPException(status_code=403, detail="Access denied")
                
                # Create annotation
                annotation = Annotation(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    user_id=user_id,
                    text=text,
                    start_time=start_time,
                    end_time=end_time,
                    annotation_type=annotation_type,
                    created_at=datetime.utcnow()
                )
                db.add(annotation)
                db.commit()
                
                return {
                    "annotation_id": annotation.id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "text": text,
                    "start_time": start_time,
                    "end_time": end_time,
                    "type": annotation_type,
                    "created_at": annotation.created_at.isoformat()
                }
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to add annotation: {e}")
            raise HTTPException(status_code=500, detail="Failed to add annotation")
    
    async def get_team_sessions(self, team_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Get all sessions shared with a team"""
        try:
            with get_db() as db:
                # Check if user is team member
                team_member = db.query(TeamMember).filter(
                    TeamMember.team_id == team_id,
                    TeamMember.user_id == user_id,
                    TeamMember.is_active == True
                ).first()
                
                if not team_member:
                    raise HTTPException(status_code=403, detail="Not a team member")
                
                # Get shared sessions
                shared_sessions = db.query(SharedSession).filter(
                    SharedSession.team_id == team_id,
                    SharedSession.is_active == True
                ).join(Session).all()
                
                sessions = []
                for shared in shared_sessions:
                    session_data = {
                        "session_id": shared.session_id,
                        "title": shared.session.title,
                        "shared_by": shared.shared_by,
                        "shared_at": shared.shared_at.isoformat(),
                        "permissions": json.loads(shared.permissions),
                        "start_time": shared.session.start_time.isoformat(),
                        "duration": shared.session.duration,
                        "status": shared.session.status
                    }
                    sessions.append(session_data)
                
                return sessions
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get team sessions: {e}")
            raise HTTPException(status_code=500, detail="Failed to get team sessions")
    
    async def get_session_comments(self, session_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Get all comments for a session"""
        try:
            with get_db() as db:
                # Check access
                session = db.query(Session).filter(Session.id == session_id).first()
                if not session:
                    raise HTTPException(status_code=404, detail="Session not found")
                
                has_access = (
                    session.user_id == user_id or
                    db.query(SharedSession).filter(
                        SharedSession.session_id == session_id,
                        SharedSession.is_active == True
                    ).join(TeamMember).filter(
                        TeamMember.user_id == user_id,
                        TeamMember.is_active == True
                    ).first() is not None
                )
                
                if not has_access:
                    raise HTTPException(status_code=403, detail="Access denied")
                
                # Get comments
                comments = db.query(Comment).filter(
                    Comment.session_id == session_id
                ).order_by(Comment.created_at).all()
                
                comment_list = []
                for comment in comments:
                    comment_data = {
                        "comment_id": comment.id,
                        "user_id": comment.user_id,
                        "content": comment.content,
                        "timestamp": comment.timestamp,
                        "created_at": comment.created_at.isoformat(),
                        "is_resolved": comment.is_resolved
                    }
                    comment_list.append(comment_data)
                
                return comment_list
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get comments: {e}")
            raise HTTPException(status_code=500, detail="Failed to get comments")
    
    async def get_session_annotations(self, session_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Get all annotations for a session"""
        try:
            with get_db() as db:
                # Check access (same as comments)
                session = db.query(Session).filter(Session.id == session_id).first()
                if not session:
                    raise HTTPException(status_code=404, detail="Session not found")
                
                has_access = (
                    session.user_id == user_id or
                    db.query(SharedSession).filter(
                        SharedSession.session_id == session_id,
                        SharedSession.is_active == True
                    ).join(TeamMember).filter(
                        TeamMember.user_id == user_id,
                        TeamMember.is_active == True
                    ).first() is not None
                )
                
                if not has_access:
                    raise HTTPException(status_code=403, detail="Access denied")
                
                # Get annotations
                annotations = db.query(Annotation).filter(
                    Annotation.session_id == session_id
                ).order_by(Annotation.start_time).all()
                
                annotation_list = []
                for annotation in annotations:
                    annotation_data = {
                        "annotation_id": annotation.id,
                        "user_id": annotation.user_id,
                        "text": annotation.text,
                        "start_time": annotation.start_time,
                        "end_time": annotation.end_time,
                        "type": annotation.annotation_type,
                        "created_at": annotation.created_at.isoformat()
                    }
                    annotation_list.append(annotation_data)
                
                return annotation_list
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get annotations: {e}")
            raise HTTPException(status_code=500, detail="Failed to get annotations")

# Global collaboration service instance
collaboration_service = CollaborationService()
