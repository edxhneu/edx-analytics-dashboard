define(function (require) {
    'use strict';

    var Backbone = require('backbone'),
        Marionette = require('marionette'),

        LearnersRouter = require('learners/app/router');

    describe('LearnersRouter', function () {
        beforeEach(function () {
            Backbone.history.start({silent: true});
            this.controller = new (Marionette.Object.extend({
                showLearnerRosterPage: function () {},
                showLearnerDetailPage: function () {},
                showNotFoundPage: function () {},
                onShowPage: function () {}
            }))();
            spyOn(this.controller, 'showLearnerRosterPage');
            spyOn(this.controller, 'showLearnerDetailPage');
            spyOn(this.controller, 'showNotFoundPage');
            spyOn(this.controller, 'onShowPage');
            this.router = new LearnersRouter({
                controller: this.controller
            });
        });

        afterEach(function () {
            // Clear previous route
            this.router.navigate('');
            Backbone.history.stop();
        });

        it('triggers a showPage event for pages beginning with "show"', function () {
            this.router.navigate('foo', {trigger: true});
            expect(this.controller.onShowPage).toHaveBeenCalled();
            this.router.navigate('/', {trigger: true});
            expect(this.controller.onShowPage).toHaveBeenCalled();
        });

        describe('showLearnerRosterPage', function () {
            beforeEach(function () {
                // Backbone won't trigger a route unless we were on a previous url
                this.router.navigate('initial-fragment', {trigger: false});
            });

            it('should trigger on an empty URL fragment', function () {
                this.router.navigate('', {trigger: true});
                expect(this.controller.showLearnerRosterPage).toHaveBeenCalled();
            });

            it('should trigger on a single forward slash', function () {
                this.router.navigate('/', {trigger: true});
                expect(this.controller.showLearnerRosterPage).toHaveBeenCalled();
            });

            it('should trigger on an empty URL fragment with a querystring', function () {
                var querystring = 'text_search=some_username';
                this.router.navigate('?' + querystring, {trigger: true});
                expect(this.controller.showLearnerRosterPage).toHaveBeenCalledWith(querystring, null);
            });
        });

        describe('showLearnerDetailPage', function () {
            it('should trigger on a username', function () {
                this.router.navigate('username', {trigger: true});
                expect(this.controller.showLearnerDetailPage).toHaveBeenCalledWith('username', null, null);
            });

            it('should trigger on a username and a trailing slash', function () {
                this.router.navigate('username/', {trigger: true});
                expect(this.controller.showLearnerDetailPage).toHaveBeenCalledWith('username', null, null);
            });

            it('should trigger on a username and a querystring', function () {
                var querystring = 'order_by=problems_attempted';
                this.router.navigate('username/?' + querystring, {trigger: true});
                expect(this.controller.showLearnerDetailPage).toHaveBeenCalledWith(
                    'username', querystring, null
                );
            });
        });

        describe('showNotFoundPage', function () {
            it('should trigger on unmatched URLs', function () {
                this.router.navigate('this/does/not/match', {trigger: true});
                expect(this.controller.showNotFoundPage).toHaveBeenCalledWith('this/does/not/match', null);
            });
        });
    });
});
