Feature: User accounts

  Background:
     Given a system specified by "default.ini"

  Scenario: A valid normal user authenticates
     Given the username is "user"
       And the password is "user"
      When the user tries to log in
      Then the login should succeed
       And the session should belong to logged in user
       And the session have user rights

  Scenario: A valid admin user authenticates
     Given the username is "admin"
       And the password is "admin"
      When the user tries to log in
      Then the login should succeed
       And the session should belong to logged in user
       And the session have admin rights

  Scenario: A valid guest user authenticates
     Given the username is "guest"
       And the password is "guest"
      When the user tries to log in
      Then the login should succeed
       And the session should belong to logged in user
       And the session have guest rights

  Scenario: An invalid user authenticates
     Given the username is "notauser"
       And the password is "notauser"
      When the user tries to log in
      Then the login should fail
       And there should not be a session

  Scenario: A valid user with the wrong password authenticates
     Given the username is "user"
       And the password is "wrong"
      When the user tries to log in
      Then the login should fail
       And there should not be a session

  Scenario: A disabled user authenticates
     Given the username is "disabled"
       And the password is "disabled"
      When the user tries to log in
      Then the login should fail
       And there should not be a session
