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

const silenceStore = Vue.reactive({
    state: {
        show: false,
        labels: {}
    },
    setLabels(labels) {
        this.state.labels = { ...labels };
    },
    addLabel(label, value) {
        this.state.labels[label] = value;
    },
    showModal() {
        this.state.show = true;
    },
    hideModal() {
        this.state.show = false;
    },
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

const app = Vue.createApp({
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
            silenceStore.setLabels(labels);
            silenceStore.showModal();
        },
        setSilenceDataset(event) {
            this.setSilenceLabels(event.target.dataset);
        },
        addSilenceLabel(label, value) {
            silenceStore.addLabel(label, value);
            silenceStore.showModal();
        },
        silenceSelectedHosts(event) {
            this.setSilenceLabels(event.target.dataset);
            this.addSilenceLabel('instance', this.selectedHosts.join('|'));
        },
        openSilenceListModal() {
            silenceListStore.showModal();
        },
        fetchSilences: function () {
            fetch('/proxy/v1/silences')
                .then(response => response.json())
                .then(response => {
                    let silences = response.sort(silence => silence.startsAt);

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
                    this.globalAlerts = response.sort(alert => alert.startsAt);
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
        },
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

app.component("silence-row", {
    delimiters: ["[[", "]]"],
    template: "#silence-row-template",
    mixins: [mixins],
    emits: ["matcherClick"],
    props: {
        silence: {
            type: Object,
            required: true,
        },
        labelColor: {
            type: String,
            default: "info",
        },
    },
});

app.component('silence-create-modal', {
    template: '#silence-create-modal-template',
    delimiters: ['[[', ']]'],
    data: () => ({
        state: silenceStore.state,
        form: {}
    }),
    computed: {
        globalMessages() {
            return globalStore.state.messages;
        },
    },
    methods: {
        addLabel() {
            if (this.form.label && this.form.value) {
                silenceStore.addLabel(this.form.label, this.form.value);
                this.form.label = '';
                this.form.value = '';
            }
        },
        removeLabel(label) {
            delete this.state.labels[label];
        },
        submit() {
            const body = JSON.stringify({
                labels: this.state.labels,
                startsAt: this.form.startsAt,
                endsAt: this.form.endsAt,
                duration: this.form.duration,
                createdBy: this.form.createdBy,
                comment: this.form.comment
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
        hideModal() {
            const modal = $('#silenceCreateModal');
            if (modal.length) {
                globalStore.setMessages([]);
                this.form = {};
                this.state = silenceStore.state;
                modal.modal('hide');
            }
        },
        showModal() {
            const modal = $('#silenceCreateModal');
            if (modal.length) {
                // Detect when the modal is closed, and update the state accordingly. This is
                // necessary in case the user closes the modal by clicking outside of it, instead of
                // using the close button.
                //
                // https://getbootstrap.com/docs/3.3/javascript/#modals-events
                modal.on('hidden.bs.modal', function (e) {
                    silenceStore.hideModal();
                });
                modal.modal('show');
            }
        },
    },
    watch: {
        "state.show"(val) {
            if (val) {
                this.showModal();
            } else {
                this.hideModal();
            }
        },
    },
});

app.component("promql-query", {
    delimiters: ['[[', ']]'],
    props: ["shard", "query", "max"],
    data: function () {
        return {
            count: 0,
            ready: false,
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
        const params = new URLSearchParams({
            shard: this.shard,
            query: this.query,
        });
        fetch(`/promql-query?${params}`)
            .then(response => response.json())
            .then(result => this.count = Number.parseInt(result.data.result[0].value[1]))
            .finally(() => this.ready = true);
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

const silenceListStore = Vue.reactive({
    state: {
        show: false,
        labels: []
    },
    addFilterLabel(label, value) {
        const existingLabel = this.state.labels.find(item => item.label === label && item.value === value);
        if (!existingLabel) {
            this.state.labels.push({ label, value });
        }
    },
    removeFilterLabel(label, value) {
        const index = this.state.labels.findIndex(item => item.label === label && item.value === value);
        if (index > -1) {
            this.state.labels.splice(index, 1);
        }
    },
    showModal() {
        this.state.show = true;
    },
    hideModal() {
        this.state.show = false;
    },
});

app.component('silence-list-modal', {
    template: '#silence-list-modal-template',
    delimiters: ['[[', ']]'],
    mixins: [mixins],
    data() {
        return {
            state: silenceListStore.state,
            form: {
                label: '',
                value: ''
            },
            store: dataStore
        };
    },
    computed: {
        activeSilences() {
            return this.$root.activeSilences || [];
        },
        filteredSilences() {
            if (!this.state.labels || this.state.labels.length === 0) {
                return this.activeSilences;
            }

            return this.activeSilences.filter(silence => {
                return this.state.labels.every(filterLabel => {
                    return silence.matchers.some(matcher => 
                        matcher.name === filterLabel.label &&
                        matcher.value === filterLabel.value
                    );
                });
            });
        },
        uniqueLabels() {
            const labels = new Set();
            this.activeSilences.forEach(silence => {
                silence.matchers.forEach(matcher => {
                    labels.add(matcher.name);
                });
            });
            return Array.from(labels).sort();
        },
        filteredValues() {
            if (!this.form.label) return [];
            const values = new Set();
            this.activeSilences.forEach(silence => {
                silence.matchers.forEach(matcher => {
                    if (matcher.name === this.form.label) {
                        values.add(matcher.value);
                    }
                });
            });
            return Array.from(values).sort();
        }
    },
    methods: {
        hideModal() {
            const modal = $('#silenceListModal');
            if (modal.length) {
                globalStore.setMessages([]);
                silenceListStore.state.labels = [];
                this.form.label = ''; 
                this.form.value = '';
                modal.modal('hide');
            }
        },
        showModal() {
            const modal = $('#silenceListModal');
            if (modal.length) {
                modal.on('hidden.bs.modal', () => {
                    silenceListStore.hideModal();
                });
                modal.modal('show');
            }
        },
        addFilterLabel(label, value) {
            if (label && value) {
                if (!this.state.labels.some(item => item.label === label && item.value === value)) {
                    silenceListStore.addFilterLabel(label, value);
                }
            } else if (this.form.label && this.form.value) {
                if (!this.state.labels.some(item => item.label === this.form.label && item.value === this.form.value)) {
                    silenceListStore.addFilterLabel(this.form.label, this.form.value);
                }
            }
            this.form.label = '';
            this.form.value = '';
        },
        removeFilterLabel(label, value) {
            silenceListStore.removeFilterLabel(label, value);
        },
        updateValueOptions() {
            this.form.value = '';
        }
    },
    watch: {
        "state.show"(val) {
            if (val) {
                this.showModal();
            } else {
                this.hideModal();
            }
        }
    },
});
