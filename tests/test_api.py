"""Tests for the Mergington High School Activities API."""

import pytest


class TestRootEndpoint:
    """Tests for the root endpoint."""

    def test_root_redirect(self, client):
        """Test that root endpoint redirects to static/index.html."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]


class TestGetActivities:
    """Tests for GET /activities endpoint."""

    def test_get_activities_success(self, client):
        """Test that get_activities returns all activities."""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert "Tennis Club" in data
        assert "Basketball Team" in data
        assert "Art Club" in data
        assert len(data) == 9  # 9 activities total

    def test_activities_have_required_fields(self, client):
        """Test that each activity has required fields."""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity in data.items():
            assert "description" in activity
            assert "schedule" in activity
            assert "max_participants" in activity
            assert "participants" in activity
            assert isinstance(activity["participants"], list)

    def test_tennis_club_initial_participants(self, client):
        """Test that Tennis Club has correct initial participants."""
        response = client.get("/activities")
        data = response.json()
        
        tennis_club = data["Tennis Club"]
        assert tennis_club["participants"] == ["alex@mergington.edu"]
        assert tennis_club["max_participants"] == 16


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint."""

    def test_signup_success(self, client):
        """Test successful signup for an activity."""
        response = client.post(
            "/activities/Tennis Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        assert "Signed up newstudent@mergington.edu for Tennis Club" in response.json()["message"]

    def test_signup_duplicate_email(self, client):
        """Test that signup fails for duplicate email."""
        # alex is already signed up for Tennis Club
        response = client.post(
            "/activities/Tennis Club/signup?email=alex@mergington.edu"
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_nonexistent_activity(self, client):
        """Test that signup fails for non-existent activity."""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_signup_updates_participants_list(self, client):
        """Test that signup updates the participants list."""
        email = "test.student@mergington.edu"
        
        # Sign up
        client.post(f"/activities/Chess Club/signup?email={email}")
        
        # Verify in activities list
        response = client.get("/activities")
        data = response.json()
        assert email in data["Chess Club"]["participants"]

    def test_signup_multiple_students(self, client):
        """Test that multiple students can sign up for same activity."""
        # Basketball Team currently has 2 participants
        email1 = "student1@mergington.edu"
        email2 = "student2@mergington.edu"
        
        response1 = client.post(f"/activities/Basketball Team/signup?email={email1}")
        response2 = client.post(f"/activities/Basketball Team/signup?email={email2}")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Verify both are signed up
        response = client.get("/activities")
        data = response.json()
        participants = data["Basketball Team"]["participants"]
        assert email1 in participants
        assert email2 in participants
        assert len(participants) == 4  # 2 original + 2 new


class TestRemoveParticipant:
    """Tests for DELETE /activities/{activity_name}/participants/{email} endpoint."""

    def test_remove_participant_success(self, client):
        """Test successful removal of a participant."""
        email = "alex@mergington.edu"
        response = client.delete(f"/activities/Tennis Club/participants/{email}")
        
        assert response.status_code == 200
        assert f"Removed {email} from Tennis Club" in response.json()["message"]

    def test_remove_participant_updates_list(self, client):
        """Test that removal updates the participants list."""
        email = "alex@mergington.edu"
        
        # Remove
        client.delete(f"/activities/Tennis Club/participants/{email}")
        
        # Verify removed
        response = client.get("/activities")
        data = response.json()
        assert email not in data["Tennis Club"]["participants"]

    def test_remove_nonexistent_participant(self, client):
        """Test that removal fails for non-existent participant."""
        response = client.delete(
            "/activities/Tennis Club/participants/nonexistent@mergington.edu"
        )
        assert response.status_code == 404
        assert "Student not found" in response.json()["detail"]

    def test_remove_from_nonexistent_activity(self, client):
        """Test that removal fails for non-existent activity."""
        response = client.delete(
            "/activities/Nonexistent Club/participants/test@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_remove_and_resign_up(self, client):
        """Test that a student can sign up again after being removed."""
        email = "alex@mergington.edu"
        
        # Remove
        client.delete(f"/activities/Tennis Club/participants/{email}")
        
        # Sign up again - should succeed
        response = client.post(f"/activities/Tennis Club/signup?email={email}")
        assert response.status_code == 200
        
        # Verify signed up
        response = client.get("/activities")
        data = response.json()
        assert email in data["Tennis Club"]["participants"]


class TestIntegration:
    """Integration tests combining multiple operations."""

    def test_complete_signup_flow(self, client):
        """Test a complete signup flow."""
        activity = "Programming Class"
        email = "integration.test@mergington.edu"
        
        # 1. Get activities
        response = client.get("/activities")
        assert response.status_code == 200
        initial_count = len(response.json()[activity]["participants"])
        
        # 2. Sign up
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
        
        # 3. Verify signup
        response = client.get("/activities")
        assert email in response.json()[activity]["participants"]
        assert len(response.json()[activity]["participants"]) == initial_count + 1
        
        # 4. Try to sign up again - should fail
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 400
        
        # 5. Remove
        response = client.delete(f"/activities/{activity}/participants/{email}")
        assert response.status_code == 200
        
        # 6. Verify removal
        response = client.get("/activities")
        assert email not in response.json()[activity]["participants"]
        assert len(response.json()[activity]["participants"]) == initial_count

    def test_email_url_encoding(self, client):
        """Test that email addresses are properly URL encoded."""
        from urllib.parse import quote
        
        email = "test+user@mergington.edu"
        encoded_email = quote(email, safe='')
        
        response = client.post(f"/activities/Art Club/signup?email={encoded_email}")
        assert response.status_code == 200
        
        response = client.get("/activities")
        assert email in response.json()["Art Club"]["participants"]
