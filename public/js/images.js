
angular.module('images', ['drahak.hotkeys', 'ngTouch'])

.config(['$httpProvider', function($httpProvider) {
    $httpProvider.defaults.headers.common["X-Requested-With"] = 'XMLHttpRequest';
}])

.controller('Entry', function ($scope, $http, $hotkey) {
    // Initialize
    $scope.tag_by_id = new Object();
    $scope.tag_feed = new Object();
    $scope.feed = new Array();
    
    $scope.reset_query = function () {
        $scope.q_start_ts = '';
        $scope.q_end_ts = '';
        $scope.q_image = 'yes';
        $scope.q_video = 'no';
        $scope.q_audio = 'no';
        $scope.q_other = 'no';
        $scope.q_show_hidden = 'no';
        $scope.q_only_hidden = 'no';
        $scope.q_show_deleted = 'no';
        $scope.q_only_deleted = 'no';
        $scope.q_include_tags = Array();
        $scope.q_exclude_tags = Array();
        $scope.q_source = '';
    };

    $scope.hk = true;

    // Modes
    $scope.mode = null;
    $scope.set_mode = function(mode) { $scope.mode = mode; };
    $scope.no_mode = function() { return $scope.mode == null; };
    $scope.query_mode = function() { return $scope.mode == 'query'; };
    $scope.tags_mode = function() { return $scope.mode == 'tags'; };
    $scope.metadata_mode = function() { return $scope.mode == 'metadata'; };
    $scope.physical_mode = function() { return $scope.mode == 'physical'; };
    $scope.debug_mode = function() { return $scope.mode == 'debug'; };
    $scope.upload_mode = function() { return $scope.mode == 'upload'; };

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
    $hotkey.bind('D', function(event) { if ($scope.hk) {
        event.preventdefault(); $scope.set_mode('debug'); }; });
    $hotkey.bind('U', function(event) { if ($scope.hk) {
        event.preventdefault(); $scope.set_mode('upload'); }; });

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
        var current_before = $scope.current;
        $http.put(entry.self_url, entry)
            .success(function(data) {
                $scope.message = "Entry updated";
                $scope.feed.entries[current_before] = data;
            });
    };

    $scope.reload = function() {
        $http.get('entry', {
            params: {
                start_ts: $scope.q_start_ts,
                end_ts: $scope.q_end_ts,
                image: $scope.q_image,
                video: $scope.q_video,
                audio: $scope.q_audio,
                other: $scope.q_other,
                show_hidden: $scope.q_show_hidden,
                only_hidden: $scope.q_only_hidden,
                show_deleted: $scope.q_show_deleted,
                only_deleted: $scope.q_only_deleted,
                include_tags: $scope.q_include_tags.join(),
                exclude_tags: $scope.q_exclude_tags.join(),
                source: $scope.q_source,
            }
        })
            .success(function(data) {
                $scope.feed = data;
                if ($scope.feed.count > 0) {
                    $scope.current = 0;
                } else {
                    $scope.current = -1;
                }
            });
    };

    $scope.reload_page = function(url, current) {
        $http.get(url)
            .success(function(data) {
                $scope.feed = data;
                if (current === 'last') {
                    $scope.current = $scope.feed.count - 1;
                } else {
                    $scope.current = 0;
                }
            });
    };

    $scope.show_from_source = function(source) {
        $scope.reset_query();
        $scope.q_source = source;
        $scope.reload();
    };

    $scope.reset_query();
    $scope.reload();

    // Tags API
    $scope.add_tag = function(event) {
        if (event.keyCode != 13) return;
        $scope.new_tag_id = document.getElementById("new_tag_id").value;
        if (!$scope.new_tag_id) { alert("Tag can't be empty!"); return; };
        var tag = new Object();
        tag.id = $scope.new_tag_id;
        tag.color_id = $scope.new_tag_color_id;
        $http.post('tag', tag)
            .success(function(tag) {
                $scope.tag_feed.entries.push(tag);
                $scope.tag_by_id[tag.id] = tag;
                $scope.new_tag_id = "";
            });
    };

    // Viewing an entry
    $scope.view = function(index) {
        $scope.current = index;
    };

    // Navigation
    $scope.previous = function() {
        if ($scope.current === 0) {
            if ($scope.feed.prev_link) {
                $scope.reload_page($scope.feed.prev_link, 'last');
            }
        } else {
            $scope.current = Math.max(0, $scope.current - 1);
        }
    };
    $hotkey.bind('Left', function(event) { if ($scope.hk) {
        event.preventDefault(); $scope.previous(); }; });

    $scope.next = function() {
        if ($scope.current === $scope.feed.count - 1) {
            if ($scope.feed.next_link) {
                $scope.reload_page($scope.feed.next_link, 'first');
            }
        } else {
            $scope.current = Math.min($scope.feed.count - 1, $scope.current + 1);
        }
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
        if (!entry) {
            return '';
        } else if (entry.access == 0) {
            return 'P';
        } else if (entry.access == 1) {
            return 'U';
        } else if (entry.access == 2) {
            return 'C';
        } else if (entry.access == 3) {
            return 'A';
        }
    };

    $scope.get_access_long = function(entry) {
        if (!entry) {
            return '';
        } else if (entry.access == 0) {
            return 'Only I can see';
        } else if (entry.access == 1) {
            return 'All users can see';
        } else if (entry.access == 2) {
            return 'All users can see and edit';
        } else if (entry.access == 3) {
            return 'Everyone can see';
        }
    };

    $scope.get_purpose = function(number) {
        if (number == 0) {
            return 'primary';
        } else if (number == 1) {
            return 'proxy';
        } else if (number == 2) {
            return 'thumb';
        } else if (number == 3) {
            return 'attachment';
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
            list.splice(a, 1);
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

    resize_proxy = function() {
        $scope.window_height = window.innerHeight + 'px';
        $scope.window_width = window.innerWidth + 'px';
        $scope.proxy_height = (window.innerHeight - 275) + 'px';
    };
    window.onresize = resize_proxy;
    resize_proxy();
})


.controller('Manage', function ($scope, $http) {
    // Modes
    $scope.mode = null;
    $scope.set_mode = function(mode) { $scope.mode = mode; };
    $scope.no_mode = function() { return $scope.mode == null; };
    $scope.location_mode = function() { return $scope.mode == 'location'; };
    $scope.import_job_mode = function() { return $scope.mode == 'import_job'; };
    $scope.deletion_mode = function() { return $scope.mode == 'deletion'; };

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

    $scope.delete = function(url) {
        $http.delete(url)
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
        9: 'archive',
        10: 'mobile',
        11: 'legacy',
    };

    $scope.purpose  ={
        0: 'primary',
        1: 'proxy',
        2: 'thumb',
        3: 'attachement',
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
        5: 'keep',
    };

    // Load resources
    $http.get('import/job')
        .success(function(data) {
            $scope.import_job_feed = data;
        });
})

.controller('Deletion', function ($scope, $http) {
    // Initialize
    $scope.delete_info = Object();

    // Load resources
    $http.get('delete')
        .success(function(data) {
            $scope.delete_info = data;
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
                if (sp) {
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
            }
        });
    }
})

.directive('imageUpload', ['$http', function($http) {
    return function(scope, element, attr) {
        element.on('change', function(event) {
            event.preventDefault();
            var
                image = element[0].files[0],
                reader = new FileReader(),
                filename = element[0].value.replace(/.*[\/\\]/, '');
            reader.onload = function(e) {
                $http.post(
                    'import/upload/web/' + filename, 
                    e.target.result, {
                        headers: { 'Content-Type': 'base64' }, })
                .then(function () {
                    scope.uploaded_image = e.target.result;
                })
            };
            reader.readAsDataURL(image);
        });
    };
}])

;
