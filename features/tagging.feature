Feature: Tagging

  @tags
  Scenario: Creating a new tag with a specific color
     Given a tag name "new.tag1"
       And a color number 6
      When the new tag is added
      Then the tag should be there
       And the color should be as specified

  @tags
  Scenario: Creating a new tag without a specific color
     Given a tag name "new.tag2"
       And no color number
      When the new tag is added
      Then the tag should be there
       And the color should be set

  @tags
  Scenario: Ensuring a tag that does not exist
     Given a tag name "new.tag3"
       And a color number 20
       And the tag is already added
      When the tag is ensured
      Then the tag should be there

  @tags
  Scenario: Ensuring a tag that does exist
     Given a tag name "new.tag4"
      When the tag is ensured
      Then the tag should be there

  @tags @entries
  Scenario: Adding one new tag to a blank entry
     Given a new entry called e
      When the tag "new.tag5" is added to the entry e
       And the entry e is updated
      Then the entry e should have the tag "new.tag5"

  @tags @entries
  Scenario: Adding one existing tag to a blank entry
     Given a new entry called e
      When the tag "new.tag5" is added to the entry e
       And the entry e is updated
      Then the entry e should have the tag "new.tag5"

  @tags @entries
  Scenario: Adding two tags to a blank entry
     Given a new entry called e
      When the tag "new.tag5" is added to the entry e
       And the tag "new.tag6" is added to the entry e
       And the entry e is updated
      Then the entry e should have the tag "new.tag5"
       And the entry e should have the tag "new.tag6"

  @tags @entries
  Scenario: Adding two tags to a two blank entries
     Given a new entry called e1
       And a new entry called e2
      When the tag "only1" is added to the entry e1
      When the tag "both" is added to the entry e1
       And the tag "both" is added to the entry e2
       And the entry e1 is updated
       And the entry e2 is updated
      Then the entry e1 should have the tag "only1"
       And the entry e1 should have the tag "both"
       And the entry e2 should not have the tag "only1"
       And the entry e2 should have the tag "both"

  @tags @entries
  Scenario: Adding two similar tags to different entries
     Given a new entry called e1
       And a new entry called e2
       And a new entry called e3
      When the tag "longer.tag" is added to the entry e1
       And the tag "longer.tag" is added to the entry e2
       And the tag "tag" is added to the entry e3
       And the entry e1 is updated
       And the entry e2 is updated
       And the entry e3 is updated
      Then a search for the tag "longer.tag" should give 2 hits
       And a search for the tag "tag" should give 1 hit
