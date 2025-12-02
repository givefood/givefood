import pytest
import json
from unittest.mock import patch, MagicMock, call
from givefood.models import Foodbank, FoodbankChange
from givefood.func import send_firebase_notification


@pytest.mark.django_db
class TestFirebaseNotifications:
    """Test Firebase Cloud Messaging notifications for food bank needs."""

    @patch('firebase_admin.messaging.send')
    @patch('firebase_admin.get_app')
    @patch('givefood.func.get_cred')
    def test_send_firebase_notification_success(self, mock_get_cred, mock_get_app, mock_send):
        """Test successful Firebase notification sending."""
        # Mock credentials
        mock_cred_dict = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "test-key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        mock_get_cred.return_value = json.dumps(mock_cred_dict)
        
        # Mock Firebase app already initialized
        mock_get_app.return_value = MagicMock()
        
        # Mock send response
        mock_send.return_value = "projects/test-project/messages/0:1234567890"
        
        # Create a food bank
        foodbank = Foodbank(
            name="Test Food Bank",
            slug="test-food-bank",
            address="Test Address",
            postcode="SW1A 1AA",
            country="England",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            network="Independent",
            url="https://test.example.com",
            shopping_list_url="https://test.example.com/shopping",
            contact_email="test@example.com",
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Create a need
        need = FoodbankChange(
            foodbank=foodbank,
            change_text="Tinned Tomatoes\nPasta\nRice\nBeans\nSoup\nCereal",
            published=True,
        )
        need.save()
        
        # Call the function
        result = send_firebase_notification(need)
        
        # Verify the result
        assert result == "projects/test-project/messages/0:1234567890"
        
        # Verify send was called with correct parameters
        assert mock_send.called
        call_args = mock_send.call_args
        message = call_args[0][0]
        
        # Check topic
        assert message.topic == f"foodbank-{foodbank.uuid}"
        
        # Check notification
        assert message.notification.title == f"{foodbank.name} needs 6 items"
        assert message.notification.body == "Tinned Tomatoes, Pasta, Rice, Beans"

    @patch('firebase_admin.credentials.Certificate')
    @patch('firebase_admin.initialize_app')
    @patch('firebase_admin.get_app')
    @patch('firebase_admin.messaging.send')
    @patch('givefood.func.get_cred')
    def test_send_firebase_notification_initializes_app(self, mock_get_cred, mock_send, mock_get_app, mock_init_app, mock_cert):
        """Test that Firebase app is initialized if not already initialized."""
        # Mock credentials
        mock_cred_dict = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "test-key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        mock_get_cred.return_value = json.dumps(mock_cred_dict)
        
        # Mock Firebase app not initialized
        mock_get_app.side_effect = ValueError("No app")
        
        # Mock certificate
        mock_cert.return_value = MagicMock()
        
        # Mock send response
        mock_send.return_value = "projects/test-project/messages/0:1234567890"
        
        # Create a food bank
        foodbank = Foodbank(
            name="Test Food Bank 2",
            slug="test-food-bank-2",
            address="Test Address",
            postcode="SW1A 1AA",
            country="England",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            network="Independent",
            url="https://test2.example.com",
            shopping_list_url="https://test2.example.com/shopping",
            contact_email="test2@example.com",
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Create a need
        need = FoodbankChange(
            foodbank=foodbank,
            change_text="Tinned Tomatoes\nPasta",
            published=True,
        )
        need.save()
        
        # Call the function
        result = send_firebase_notification(need)
        
        # Verify initialize_app was called
        assert mock_init_app.called
        
        # Verify send was still called
        assert mock_send.called

    @patch('firebase_admin.get_app')
    @patch('givefood.func.get_cred')
    def test_send_firebase_notification_no_credentials(self, mock_get_cred, mock_get_app):
        """Test that function returns None when credentials are not available."""
        # Mock no credentials
        mock_get_cred.return_value = None
        
        # Mock Firebase app not initialized
        mock_get_app.side_effect = ValueError("No app")
        
        # Create a food bank
        foodbank = Foodbank(
            name="Test Food Bank 3",
            slug="test-food-bank-3",
            address="Test Address",
            postcode="SW1A 1AA",
            country="England",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            network="Independent",
            url="https://test3.example.com",
            shopping_list_url="https://test3.example.com/shopping",
            contact_email="test3@example.com",
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Create a need
        need = FoodbankChange(
            foodbank=foodbank,
            change_text="Tinned Tomatoes",
            published=True,
        )
        need.save()
        
        # Call the function
        result = send_firebase_notification(need)
        
        # Verify the result is None
        assert result is None

    @patch('firebase_admin.messaging.send')
    @patch('firebase_admin.get_app')
    @patch('givefood.func.get_cred')
    def test_send_firebase_notification_handles_errors(self, mock_get_cred, mock_get_app, mock_send):
        """Test that function handles errors gracefully."""
        # Mock credentials
        mock_cred_dict = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "test-key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        mock_get_cred.return_value = json.dumps(mock_cred_dict)
        
        # Mock Firebase app already initialized
        mock_get_app.return_value = MagicMock()
        
        # Mock send raises an exception
        mock_send.side_effect = Exception("Network error")
        
        # Create a food bank
        foodbank = Foodbank(
            name="Test Food Bank 4",
            slug="test-food-bank-4",
            address="Test Address",
            postcode="SW1A 1AA",
            country="England",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            network="Independent",
            url="https://test4.example.com",
            shopping_list_url="https://test4.example.com/shopping",
            contact_email="test4@example.com",
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Create a need
        need = FoodbankChange(
            foodbank=foodbank,
            change_text="Tinned Tomatoes",
            published=True,
        )
        need.save()
        
        # Call the function
        result = send_firebase_notification(need)
        
        # Verify the result is None (error was caught)
        assert result is None

    @patch('firebase_admin.messaging.send')
    @patch('firebase_admin.get_app')
    @patch('givefood.func.get_cred')
    def test_send_firebase_notification_formats_correctly(self, mock_get_cred, mock_get_app, mock_send):
        """Test that notification is formatted correctly with first 4 items."""
        # Mock credentials
        mock_cred_dict = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "test-key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        mock_get_cred.return_value = json.dumps(mock_cred_dict)
        
        # Mock Firebase app already initialized
        mock_get_app.return_value = MagicMock()
        
        # Mock send response
        mock_send.return_value = "projects/test-project/messages/0:1234567890"
        
        # Create a food bank
        foodbank = Foodbank(
            name="Test Food Bank 5",
            slug="test-food-bank-5",
            address="Test Address",
            postcode="SW1A 1AA",
            country="England",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            network="Independent",
            url="https://test5.example.com",
            shopping_list_url="https://test5.example.com/shopping",
            contact_email="test5@example.com",
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Create a need with exactly 4 items
        need = FoodbankChange(
            foodbank=foodbank,
            change_text="Item 1\nItem 2\nItem 3\nItem 4",
            published=True,
        )
        need.save()
        
        # Call the function
        result = send_firebase_notification(need)
        
        # Verify send was called
        assert mock_send.called
        call_args = mock_send.call_args
        message = call_args[0][0]
        
        # Check that all 4 items are in the body
        assert message.notification.body == "Item 1, Item 2, Item 3, Item 4"
