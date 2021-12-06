/*
 * Copyright (c) 2021 LINE Corporation
 * These sources are released under the terms of the MIT license: see LICENSE
 */

Vue.config.devtools = true

const dataStore = {
    components: {},
    selectedHosts: [],
    newSilence: { 'labels': {} },
    globalSilences: [],
    globalAlerts: [],
    globalMessages: []
};

const app = new Vue({
    el: '#vue',
    delimiters: ['[[', ']]'],
    data: dataStore,
    methods: {
        toggleComponent: function (component) {
            let state = Boolean(this.components[component]);
            this.$set(this.components, component, !state);
        },
        toggleCollapse: function (target) {
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
            this.$set(this.components, 'silence-form', true);
            scroll(0, 0);
        },
        silenceAppendLabel: function (event) {
            console.debug('silenceAppendLabel', event.target.dataset);
            this.$set(this.newSilence.labels, event.target.dataset.label, event.target.dataset.value);
            this.showSilenceForm(event);
        },
        silenceSelectedHosts: function (event) {
            this.$set(this.newSilence, 'labels', {});
            this.$set(this.newSilence.labels, "instance", this.selectedHosts.join("|"));
            for (key in event.target.dataset) {
                this.$set(this.newSilence.labels, key, event.target.dataset[key]);
            }
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
                .then(function (response) {
                    let silences = response.data.sort(silence => silence.startsAt);

                    // Pull out the matchers and do a simpler label map
                    // to make other code easier
                    for (let silence of silences) {
                        silence.labels = {};
                        for (let matcher of silence.matchers) {
                            silence.labels[matcher.name] = matcher.value;
                        }
                    }

                    this_.globalSilences = silences;
                });
        },
        fetchAlerts: function () {
            let this_ = this;
            fetch('/proxy/v1/alerts')
                .then(response => response.json())
                .then(function (response) {
                    this_.globalAlerts = response.data.sort(alert => alert.startsAt);
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
        activeServiceAlerts: function () {
            return groupByLabel(this.activeAlerts, 'service');
        },
        activeProjectAlerts: function () {
            return groupByLabel(this.activeAlerts, 'project');
        },
        activeRuleAlerts: function () {
            return groupByLabel(this.activeAlerts, 'alertname');
        },
        activeServiceSilences: function () {
            return groupByLabel(this.activeSilences, 'service');
        },
        activeProjectSilences: function () {
            return groupByLabel(this.activeSilences, 'project');
        },
        activeAlerts: function () {
            return this.globalAlerts.filter(alert => alert.status.state == 'active');
        },
        activeSilences: function () {
            return this.globalSilences.filter(silence => silence.status.state != 'expired');
        }
    },
    mounted: function () {
        this.fetchAlerts();
        this.fetchSilences();
    },
});

Vue.filter("localize", function (number) {
    return number.toLocaleString();
});

Vue.filter("percent", function (number) {
    return (number * 100).toLocaleString() + "%"
});

Vue.filter("urlize", function (value) {
    return linkifyStr(value);
});

Vue.filter("time", function (value, fmtstr = "YYYY-MM-DD HH:mm:ss") {
    return moment(value).format(fmtstr);
});

Vue.component("promql-query", {
    props: ["href", "query", "max"],
    data: function () {
        return {
            count: 0,
        };
    },
    computed: {
        load: function () {
            return this.count / Number.parseInt(this.max);
        },
        classes: function () {
            if (this.load > 0.9) return "label label-danger";
            if (this.load > 0.7) return "label label-warning";
            if (this.load > 0.5) return "label label-info";
            if (this.count == 0) return "label label-default";
            return "label label-success";
        },
    },
    template: `
    <span style="display:none" :title="load|percent" :class="classes">
        {{count|localize}} <slot></slot>
    </span>
    `,
    mounted() {
        var this_ = this;
        var url = new URL(this.href);
        url.search = new URLSearchParams({ query: this.query });
        fetch(url)
            .then(response => response.json())
            .then(result => Number.parseInt(result.data.result[0].value[1]))
            .then(result => {
                this_.count = result;
                this_.$el.style.display = "inline";
            })
            .catch(error => {
                this_.$el.style.display = "inline";
            });
    },
});

Vue.component('bootstrap-panel', {
    props: ['heading'],
    template: '<div class="panel"><div class="panel-heading">{{heading}}</div><div class="panel-body"><slot /></div></div>'
})

const ExporterResult = Vue.component('exporter-result', {
    props: ['results'],
    template: '<bootstrap-panel class="panel-info" heading="Results"><table class="table"><tr v-for="(val, key, index) in results"><td>{{key}}</td><td>{{val}}</td></tr></table></bootstrap-panel>'
})

const ExporterTest = Vue.component('exporter-test', {
    // Exporter Test button for Forms
    // Acts like a regular form submit button, but hijacks the button
    // click and submits it to an alternate URL for testing
    props: ['href', 'target'],
    template: '<button @click.prevent="onTestSubmit"><slot /></button>',
    methods: {
        onTestSubmit: function (event) {
            // Find the parent form our button belongs to so that we can
            // simulate a form submission
            let form = new FormData(event.srcElement.closest('form'))
            let tgt = document.querySelector(this.target);
            fetch(this.href, { body: form, method: "post", })
                .then(result => result.json())
                .then(result => {
                    // If we have a valid result, then create a new
                    // ExporterResult component that we can render
                    var component = new ExporterResult().$mount(tgt);
                    component.$el.id = tgt.id;
                    component.$props.results = result;
                })
                .catch(error => alert(error))
        }
    }
})
