Feature: User accounts

  Scenario: A valid user authenticates
     Given the username is "user"
       And the password is "user"
      When the user tries to log in
      Then the login should succeed

  Scenario: A invalid user authenticates
     Given the username is "notauser"
       And the password is "notauser"
      When the user tries to log in
      Then the login should fail

  Scenario: A valid user with the wrong password authenticates
     Given the username is "user"
       And the password is "wrong"
      When the user tries to log in
      Then the login should fail
