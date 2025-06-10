from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

class EmailOrUsernameModelBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in using their email or username.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        
        try:
            # Try to fetch the user by email or username
            user = UserModel.objects.get(
                Q(username__iexact=username) | 
                Q(email__iexact=username)
            )
            
            # Verify the password
            if user.check_password(password):
                return user
                
        except UserModel.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a non-existing user.
            UserModel().set_password(password)
            
        except UserModel.MultipleObjectsReturned:
            # If multiple users are found, return None to prevent security issues
            return None
            
        return None
    
    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            return UserModel._default_manager.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
