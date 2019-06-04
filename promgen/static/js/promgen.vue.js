/*
# Copyright (c) 2019 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
*/

Vue.config.devtools = true

var dataStore = {
    newSilence: { 'labels': {} },
    globalSilences: [],
    globalAlerts: [],
    globalMessages: []
};

var app = new Vue({
    el: '#vue',
    data: dataStore,
    methods: {
        toggleTarget: function (target) {
            let tgt = document.getElementById(target);
            tgt.classList.toggle('collapse');
        },
        silenceExpire: function (id) {
            fetch('/proxy/v1/silences/' + id, { method: 'DELETE' }).then(function (response) {
                location.reload();
            })
        },
        silenceChangeEvent: function (event) {
            this.newSilence[event.target.name] = event.target.value;
        },
        silenceSubmit: function (event) {
            let this_ = this;
            fetch('/proxy/v1/silences', { method: 'POST', body: JSON.stringify(this.newSilence) })
                .then(function (response) {
                    if (response.ok) {
                        location.reload();
                    } else {
                        return response.json()
                    }
                })
                .then(function (result) {
                    this_.globalMessages = [];
                    for (key in result.messages) {
                        this_.$set(this_.globalMessages, key, result.messages[key]);
                    }
                })
        },
        silenceRemoveLabel: function (label) {
            console.debug('silenceRemoveLabel', label)
            this.$delete(this.newSilence.labels, label)
        },
        showSilenceForm: function (event) {
            document.getElementById('silence-form').classList.remove('collapse');
            scroll(0, 0);
        },
        silenceAppendLabel: function (event) {
            console.debug('silenceAppendLabel', event.target.dataset);
            this.$set(this.newSilence.labels, event.target.dataset.label, event.target.dataset.value);
            this.showSilenceForm(event);
        },
        silenceSetLabels: function (event) {
            console.debug('silenceSetLabels', event.target.dataset);
            this.$set(this.newSilence, 'labels', {});
            for (key in event.target.dataset) {
                this.$set(this.newSilence.labels, key, event.target.dataset[key]);
            }
            this.showSilenceForm(event);
        },
        silenceAlert: function (alert) {
            this.$set(this.newSilence, 'labels', {});
            for (key in alert.labels) {
                this.$set(this.newSilence.labels, key, alert.labels[key]);
            }
            this.showSilenceForm(event);
        },
        fetchSilences: function () {
            let this_ = this;
            fetch('/proxy/v1/silences')
                .then(response => response.json())
                .then(function (silences) {
                    this_.globalSilences = silences.data.sort(silence => silence.startsAt);

                    // Pull out the matchers and do a simpler label map
                    // To make other code easier
                    for (var i in this_.globalSilences) {
                        var silence = this_.globalSilences[i];
                        silence.labels = {}
                        for (var m in silence.matchers) {
                            let matcher = silence.matchers[m]
                            silence.labels[matcher.name] = matcher.value
                        }
                    }
                });
        },
        fetchAlerts: function () {
            let this_ = this;
            fetch('/proxy/v1/alerts')
                .then(response => response.json())
                .then(function (alerts) {
                    this_.globalAlerts = alerts.data.sort(alert => alert.startsAt);
                });

        },
        setTargetList: function (event, target) {
            // get the list name
            let dst = event.target.list.id;
            // and our selected value
            let src = event.target.value;
            // and set the target list
            let tgt = document.getElementById(target);
            tgt.setAttribute('list', dst + '.' + src);
        }
    },
    computed: {
        alertLabelsService: function () {
            return new Set(this.globalAlerts
                .filter(x => x.status.state == 'active')
                .filter(x => x.labels.service)
                .map(x => x.labels.service)
                .sort()
            );
        },
        alertLabelsProject: function () {
            return new Set(this.globalAlerts
                .filter(x => x.status.state == 'active')
                .filter(x => x.labels.project)
                .map(x => x.labels.project)
                .sort()
            );
        },
        alertLabelsRule: function () {
            return new Set(this.globalAlerts
                .filter(x => x.status.state == 'active')
                .filter(x => x.labels.alertname)
                .map(x => x.labels.alertname)
                .sort()
            );
        },
        silenceLabelsService: function () {
            return new Set(this.globalSilences
                .filter(x => x.status.state == 'active')
                .filter(x => x.labels.service)
                .map(x => x.labels.service)
                .sort()
            );
        },
        silenceLabelsProject: function () {
            return new Set(this.globalSilences
                .filter(x => x.status.state == 'active')
                .filter(x => x.labels.project)
                .map(x => x.labels.project)
                .sort()
            );
        },
        filterActiveAlerts: function () {
            return this.globalAlerts.filter(alert => alert.status.state == 'active');
        },
        filterActiveSilences: function () {
            return this.globalSilences.filter(silence => silence.status.state != 'expired');
        }
    },
    mounted: function () {
        this.fetchAlerts();
        this.fetchSilences();
    },
    filters: {
        urlize: function (value) {
            return linkifyStr(value);
        },
        time: function (value, fmtstr = 'YYYY-MM-DD HH:mm:ss') {
            return moment(value).format(fmtstr);
        }
    }
})
