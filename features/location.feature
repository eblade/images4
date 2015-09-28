Feature: Locations

  @locations
  Scenario: Adding locations
     Given a specific set of location data
        | name      | type        | path                    | keep original   | user id   | access  |
        | test_drop | drop_folder | /tmp/images/drop_folder | no              | 1         | private |
        | test_mob  | mobile      | /tmp/images/mobile      | yes             | 2         | users   |
        | test_leg  | legacy      | /tmp/images/legacy      | yes             | 2         | public  |

      Then there should be a "drop_folder" location named "test_drop"
       And that location should be mounted at "/tmp/images/drop_folder"
       And that location should not keep originals
       And that location should have private access
       And that location should belong to user 1

      Then there should be a "mobile" location named "test_mob"
       And that location should be mounted at "/tmp/images/mobile"
       And that location should keep originals
       And that location should have users access
       And that location should belong to user 2

      Then there should be a "legacy" location named "test_leg"
       And that location should be mounted at "/tmp/images/legacy"
       And that location should keep originals
       And that location should have public access
       And that location should belong to user 2

