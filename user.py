class AppUser:
    """
    User class representing the current authenticated user.
    Contains personal information used when generating emails.
    """
    name = None
    surname = None
    email = None
    label_id_encode_dict = {

    }


    @classmethod
    def get_full_name(cls):
        """Return the user's full name"""
        if cls.name and cls.surname:
            return f"{cls.name} {cls.surname}"
        elif cls.name:
            return cls.name
        else:
            return "User"
    
    @classmethod
    def set_user_info(cls, name=None, surname=None, email=None):
        """Set user information manually"""
        if name:
            cls.name = name
        if surname:
            cls.surname = surname
        if email:
            cls.email = email



