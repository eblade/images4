Feature: Exporing entries

  Background:
     Given a system specified by "default.ini"
       And a specific set of locations
        | name             | type        | folder           | wants   |
        | test_exp_primary | export      | /tmp/images/exp1 | primary |
        | test_exp_proxy   | export      | /tmp/images/exp2 | proxy   |

  Scenario: Creating an export job
     Given the user logged in as user:user
       And an entry called e
      When the user creates a specific set of export jobs
        | entry_id | location         | path            |
        | 1        | test_exp_primary | test_file.jpeg  |
      Then the entry with id 1 should have the following export jobs
        | entry_id | location         | path            | user |
        | 1        | test_exp_primary | test_file.jpeg  | user |

  Scenario: Creating two export jobs for the same entry
     Given the user logged in as user:user
       And an entry called e
      When the user creates a specific set of export jobs
        | entry_id | location         | path            |
        | 1        | test_exp_primary | test_file1.jpeg |
        | 1        | test_exp_proxy   | test_file2.jpeg |
      Then the entry with id 1 should have the following export jobs
        | entry_id | location         | path            | user |
        | 1        | test_exp_primary | test_file1.jpeg | user |
        | 1        | test_exp_proxy   | test_file2.jpeg | user |

  Scenario: Creating two export jobs for different entries
     Given the user logged in as user:user
       And an entry called e1
       And an entry called e2
      When the user creates a specific set of export jobs
        | entry_id | location         | path            |
        | 1        | test_exp_primary | test_file1.jpeg |
        | 2        | test_exp_proxy   | test_file2.jpeg |
      Then the entry with id 1 should have the following export jobs
        | entry_id | location         | path            | user |
        | 1        | test_exp_primary | test_file1.jpeg | user |
       And the entry with id 2 should have the following export jobs
        | entry_id | location         | path            | user |
        | 2        | test_exp_proxy   | test_file2.jpeg | user |

  Scenario: It should be possible to get a list of export locations for an entry
      Then possible export destinations should be as follows
        | name             |
        | test_exp_primary |
        | test_exp_proxy   |
