/*
 * Copyright (c) 2021 LINE Corporation
 * These sources are released under the terms of the MIT license: see LICENSE
 */

const globalStore = Vue.reactive({
    state: {
        messages: []
    },
    setMessages(messages) {
        this.state.messages = [...messages];
    }
});

const dataStore = Vue.reactive({
    global: globalStore.state,
    components: {},
    selectedHosts: [],
    globalSilences: [],
    globalAlerts: []
});

const exporterTestResultStore = Vue.reactive({
    results: {},
    addResult(url, statusCode) {
        this.results[url] = statusCode;
    },
    setResults(results) {
        this.results = { ...results };
    },
});

const app = createPrimeVueApp({
    delimiters: ['[[', ']]'],
    data() {
        return dataStore;
    },
    mixins: [mixins],
    methods: {
        toggleComponent: function (component) {
            let state = Boolean(this.components[component]);
            this.components[component] = !state;
        },
        toggleCollapse: function (target) {
            let tgt = document.getElementById(target);
            tgt.classList.toggle('collapse');
        },
        expireSilence(id) {
            fetch(`/proxy/v1/silences/${id}`, { method: 'DELETE' })
                .then(() => location.reload());
        },
        setSilenceLabels(labels) {
            const silenceStore = useSilenceStore();
            silenceStore.setLabels(labels);
            silenceStore.showForm();
            scroll(0, 0);
        },
        setSilenceDataset(event) {
            this.setSilenceLabels(event.target.dataset);
        },
        addSilenceLabel(label, value) {
            const silenceStore = useSilenceStore();
            silenceStore.addLabel(label, value);
            silenceStore.showForm();
            scroll(0, 0);
        },
        silenceSelectedHosts(event) {
            this.setSilenceLabels(event.target.dataset);
            this.addSilenceLabel('instance', this.selectedHosts.join('|'));
        },
        fetchSilences: function () {
            fetch('/proxy/v1/silences')
                .then(response => response.json())
                .then(response => {
                    let silences = response.data.sort(silence => silence.startsAt);

                    // Pull out the matchers and do a simpler label map
                    // to make other code easier
                    for (let silence of silences) {
                        silence.labels = {};
                        for (let matcher of silence.matchers) {
                            silence.labels[matcher.name] = matcher.value;
                        }
                    }

                    this.globalSilences = silences;
                });
        },
        fetchAlerts: function () {
            fetch('/proxy/v1/alerts')
                .then(response => response.json())
                .then(response => {
                    this.globalAlerts = response.data.sort(alert => alert.startsAt);
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
            return this.globalAlerts.filter(alert => alert.status.state === 'active');
        },
        activeSilences: function () {
            return this.globalSilences.filter(silence => silence.status.state !== 'expired');
        }
    },
    mounted: function () {
        this.fetchAlerts();
        this.fetchSilences();
    },
});

app.config.compilerOptions.whitespace = "preserve";

app.component('silence-form', {
    template: '#silence-form-template',
    delimiters: ['[[', ']]'],
    data: () => ({
        state: useSilenceStore(),
        form: {}
    }),
    methods: {
        submit() {
            const body = JSON.stringify({
                labels: this.state.labels,
                ...this.form
            });

            fetch('/proxy/v1/silences', { method: 'POST', body })
                .then(response => {
                    if (response.ok) {
                        location.reload();
                    } else {
                        return response.json();
                    }
                })
                .then(result => {
                    if (result) {
                        globalStore.setMessages(result.messages);
                    }
                });
        },
    }
});

app.component("promql-query", {
    delimiters: ['[[', ']]'],
    props: ["href", "query", "max"],
    data: function () {
        return {
            count: 0,
        };
    },
    mixins: [mixins],
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
    template: '#promql-query-template',
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

app.component('bootstrap-panel', {
    delimiters: ['[[', ']]'],
    props: ['heading'],
    template: '#bootstrap-panel-template',
});

app.component('exporter-result', {
    delimiters: ['[[', ']]'],
    props: ['results'],
    template: '#exporter-result-template',
    data: () => ({
        store: exporterTestResultStore,
    }),
    computed: {
        show() {
            return Object.keys(this.store.results).length > 0;
        },
    },
});

app.component('exporter-test', {
    // Exporter Test button for Forms
    // Acts like a regular form submit button, but hijacks the button
    // click and submits it to an alternate URL for testing
    delimiters: ['[[', ']]'],
    props: ['href'],
    template: '#exporter-test-template',
    methods: {
        onTestSubmit: function (event) {
            // Find the parent form our button belongs to so that we can
            // simulate a form submission
            let form = new FormData(event.srcElement.closest('form'))
            fetch(this.href, { body: form, method: "post", })
                .then(result => result.json())
                .then(result => exporterTestResultStore.setResults(result))
                .catch(error => alert(error))
        }
    }
});
