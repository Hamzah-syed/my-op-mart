Feature: User management
  Scenario: Create a new user
    Given the user does not exist
    When I send a POST request to "/users/" with the user data
    Then the response status should be 200
    And the response should contain the user data
