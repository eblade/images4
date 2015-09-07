
angular.module('images', ['drahak.hotkeys', 'ngTouch'])

.config(['$httpProvider', function($httpProvider) {
    $httpProvider.defaults.headers.common["X-Requested-With"] = 'XMLHttpRequest';
}])

.controller('Entry', function ($scope, $http, $hotkey) {
    // Initialize
    $scope.tag_by_id = new Object();
    $scope.tag_feed = new Object();
    $scope.feed = new Array();
    
    $scope.q_start_ts = '2000-01-01';
    $scope.q_end_ts = '';
    $scope.q_show_hidden = 'no';
    $scope.q_only_hidden = 'no';
    $scope.q_show_deleted = 'no';
    $scope.q_only_deleted = 'no';
    $scope.q_include_tags = Array();
    $scope.q_exclude_tags = Array();

    $scope.hk = true;

    // Modes
    $scope.mode = null;
    $scope.set_mode = function(mode) { $scope.mode = mode; };
    $scope.no_mode = function() { return $scope.mode == null; };
    $scope.query_mode = function() { return $scope.mode == 'query'; };
    $scope.tags_mode = function() { return $scope.mode == 'tags'; };
    $scope.metadata_mode = function() { return $scope.mode == 'metadata'; };
    $scope.physical_mode = function() { return $scope.mode == 'physical'; };

    $hotkey.bind('N', function(event) { if ($scope.hk) {
        event.preventDefault(); $scope.set_mode(null); }; });
    $hotkey.bind('Q', function(event) { if ($scope.hk) {
        event.preventDefault(); $scope.set_mode('query'); }; });
    $hotkey.bind('T', function(event) { if ($scope.hk) {
        event.preventDefault(); $scope.set_mode('tags'); }; });
    $hotkey.bind('M', function(event) { if ($scope.hk) {
        event.preventDefault(); $scope.set_mode('metadata'); }; });
    $hotkey.bind('P', function(event) { if ($scope.hk) {
        event.preventDefault(); $scope.set_mode('physical'); }; });

    $scope.enable_hk = function() {
        $scope.hk = true;
    };

    $scope.disable_hk = function() {
        $scope.hk = false;
    };

    // Load resources
    $http.get('tag')
        .success(function(data) {
            $scope.tag_feed = data;
            $scope.tag_by_id = new Object();
            angular.forEach($scope.tag_feed.entries, function(tag) {
                $scope.tag_by_id[tag.id] = tag;
            });
        });

    $http.get('user/me')
        .success(function(data) {
            $scope.me = data;
        });


    // Entry API
    $scope.update_entry = function(entry) {
        $http.put(entry.self_url, entry)
            .success(function(data) {
                $scope.message = "Entry updated";
            });
    };

    $scope.reload = function() {
        $http.get('entry', {
            params: {
                start_ts: $scope.q_start_ts,
                end_ts: $scope.q_end_ts,
                show_hidden: $scope.q_show_hidden,
                only_hidden: $scope.q_only_hidden,
                show_deleted: $scope.q_show_deleted,
                only_deleted: $scope.q_only_deleted,
                include_tags: $scope.q_include_tags.join(),
                exclude_tags: $scope.q_exclude_tags.join(),
            }
        })
            .success(function(data) {
                $scope.feed = data;
            });
    };

    $scope.reload();

    // Tags API
    $scope.add_tag = function(event) {
        if (event.keyCode != 13) return;
        var tag = new Object();
        tag.id = $scope.new_tag_id;
        tag.color_id = $scope.new_tag_color_id;
        $scope.new_tag_id = "";
        $http.post('tag', tag)
            .success(function(tag) {
                $scope.tag_feed.entries.push(tag);
                $scope.tag_by_id[tag.id] = tag;
            });
    };

    // Viewing an entry
    $scope.view = function(index) {
        $scope.current = index;
    };

    // Navigation
    $scope.previous = function() {
        $scope.current = Math.max(0, $scope.current - 1);
    };
    $hotkey.bind('Left', function(event) { if ($scope.hk) {
        event.preventDefault(); $scope.previous(); }; });

    $scope.next = function() {
        $scope.current = Math.min($scope.feed.count - 1, $scope.current + 1);
    };
    $hotkey.bind('Right', function(event) { if ($scope.hk) {
        event.preventDefault(); $scope.next(); }; });

    $scope.home = function() {
        $scope.current = 0;
    };
    $hotkey.bind('Ctrl+Left', function(event) { if ($scope.hk) {
        event.preventDefault(); $scope.home(); }; });

    $scope.end = function() {
        $scope.current = $scope.feed.count - 1;
    };
    $hotkey.bind('Ctrl+Right', function(event) { if ($scope.hk) {
        event.preventDefault(); $scope.end(); }; });

    $hotkey.bind('Enter', function(event) { if ($scope.query_mode()) {
        event.preventDefault(); $scope.reload(); }; });

    // Toggling Delete
    $scope.toggle_deleted = function() {
        var entry = $scope.feed.entries[$scope.current];
        entry.deleted = ! entry.deleted;
        $scope.update_entry(entry);
    };
    $hotkey.bind('Delete', function(event) { if ($scope.hk) {
        event.preventDefault(); $scope.toggle_deleted(); }; });

    // Toggling Hidden
    $scope.toggle_hidden = function() {
        var entry = $scope.feed.entries[$scope.current];
        entry.hidden = ! entry.hidden;
        $scope.update_entry(entry);
    };
    $hotkey.bind('X', function(event) { if ($scope.hk) {
        event.preventDefault(); $scope.toggle_hidden(); }; });

    // Info About Current
    $scope.have_current = function() {
        if ($scope.current < 0) {
            return false;
        } else {
            return true;
        }
    };

    $scope.get_current = function() {
        var entry;
        if ($scope.current < 0) { return null; }
        if ($scope.feed == null) { return null; }
        return $scope.feed.entries[$scope.current];
    };

    $scope.get_current_proxy_url = function() {
        if ($scope.current < 0) {
            return ''
        } else {
            return $scope.feed.entries[$scope.current].proxy_url;
        }
    };

    $scope.get_current_filename = function() {
        if ($scope.current < 0) {
            return ''
        } else {
            return $scope.feed.entries[$scope.current].original_filename;
        }
    };

    $scope.get_filters = function(index, entry) {
        var filters = "";
        if (entry.deleted == true) {
            filters += " deleted";
        }
        else if (entry.hidden == true) {
            filters += " hidden";
        }
        if (index == $scope.current) {
            filters += " selected";
        }
        return filters;
    };

    $scope.current_is_deleted = function() {
        var entry = $scope.get_current();
        return entry ? entry.deleted : false;
    }

    $scope.current_is_hidden = function() {
        var entry = $scope.get_current();
        return entry ? entry.hidden : false;
    }

    $scope.get_access = function(entry) {
        if (entry.access == 0) {
            return 'P';
        } else if (entry.access == 1) {
            return 'U';
        } else if (entry.access == 2) {
            return 'C';
        } else if (entry.access == 3) {
            return 'A';
        }
    };

    // Tags functions
    $scope.list_have = function(string, list) {
        var a = list.indexOf(string);
        if (a === -1) { return "no"; }
        else { return "yes"; }
    };

    $scope.list_toggle = function(string, list) {
        var a = list.indexOf(string);
        if (a === -1) {
            list.push(string);
        } else {
            list.splice(a);
        }
    };

    $scope.have_tag = function(tag_id) {
        var entry;
        entry = $scope.get_current();
        if (entry == null) { return "no"; }
        return $scope.list_have(tag_id, entry.tags);
    };

    $scope.toggle_tag = function(tag_id) {
        var entry = $scope.feed.entries[$scope.current];
        if (entry == null) {
            return;
        }
        $scope.list_toggle(tag_id, entry.tags);
        $scope.update_entry(entry);
    };

    $scope.tag_background_color = function(tag_id) {
        var tag = $scope.tag_by_id[tag_id];
        if (tag == null) {
            return 'black';
        }
        return tag.background_color;
    };
    
    $scope.tag_foreground_color = function(tag_id) {
        var tag = $scope.tag_by_id[tag_id];
        if (tag == null) {
            return 'white';
        }
        return tag.foreground_color;
    };
})


.controller('Manage', function ($scope, $http) {
    // Modes
    $scope.mode = null;
    $scope.set_mode = function(mode) { $scope.mode = mode; };
    $scope.no_mode = function() { return $scope.mode == null; };
    $scope.location_mode = function() { return $scope.mode == 'location'; };
    $scope.import_job_mode = function() { return $scope.mode == 'import_job'; };

    // Load resources
    $http.get('user/me')
        .success(function(data) {
            $scope.me = data;
        });

    $scope.empty_post = function(url) {
        $http.post(url)
            .success(function(data) {
                $scope.message = data.result;
            });
    };

    $scope.bool2str = function(b) {
        return b ? 'yes' : 'no';
    }
})

.controller('Location', function ($scope, $http) {
    // Initialize
    $scope.location_feed = Array();
    $scope.location_type = {
        0: 'drop_folder',
        1: 'image',
        2: 'video',
        3: 'audio',
        4: 'other',
        5: 'proxy',
        6: 'thumb',
        7: 'upload',
        8: 'export',
    };

    // Load resources
    $http.get('location')
        .success(function(data) {
            $scope.location_feed = data;
        });
})

.controller('ImportJob', function ($scope, $http) {
    // Initialize
    $scope.import_job_feed = Array();
    $scope.import_job_state = {
        0: 'new',
        1: 'active',
        2: 'done',
        3: 'failed',
        4: 'hold',
    };

    // Load resources
    $http.get('import/job')
        .success(function(data) {
            $scope.import_job_feed = data;
        });
})

.directive('scrollIf', function () {
    var getScrollingParent = function(element) {
        element = element.parentElement;
        while (element) {
            if (element.scrollWidth !== element.clientWidth) {
                return element;
            }
            element = element.parentElement;
        }
        return null;
    };
    return function (scope, element, attrs) {
        scope.$watch(attrs.scrollIf, function(value) {
            if (value) {
                var sp = getScrollingParent(element[0]);
                var leftMargin = parseInt(attrs.scrollMarginLeft) || 0;
                var rightMargin = parseInt(attrs.scrollMarginRight) || 0;
                var elemOffset = element[0].offsetLeft;
                var elemWidth = element[0].clientWidth;

                if (elemOffset - leftMargin < sp.scrollLeft) {
                    sp.scrollLeft = elemOffset - leftMargin;
                } else if (elemOffset + elemWidth + rightMargin > sp.scrollLeft + sp.clientWidth) {
                    sp.scrollLeft = elemOffset + elemWidth + rightMargin - sp.clientWidth;
                }
            }
        });
    }
})

;
