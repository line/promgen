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
        for (const [key, value] of Object.entries(this.state.labels)) {
            if (!Array.isArray(value)) {
                if (value.includes("*")) {
                    this.state.labels[key] = [value, "=~"];
                } else {
                    this.state.labels[key] = [value, "="];
                }
            }
        }
    },
    addLabel(label, value) {
        if (Array.isArray(value) && value[1] === undefined) {
            if (value[0].includes("*")) {
                value[1] = "=~";
            } else {
                value[1] = "=";
            }
        }
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
        addSilenceLabel(label, value, operator) {
            silenceStore.addLabel(label, [value, operator]);
            silenceStore.showModal();
        },
        silenceSelectedHosts(event) {
            this.setSilenceLabels(event.target.dataset);
            this.addSilenceLabel('instance', this.selectedHosts.join('|'));
        },
        openSilenceListModal(params) {
            silenceListStore.showModal(params);
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
    methods: {
        getOperator(matcher) {
            if (matcher.isEqual) {
                if (matcher.isRegex) {
                    return "=~";
                } else {
                    return "=";
                }
            } else {
                if (matcher.isRegex) {
                    return "!~";
                } else {
                    return "!=";
                }
            }
        },
    },
});

app.component('silence-create-modal', {
    template: '#silence-create-modal-template',
    delimiters: ['[[', ']]'],
    data: () => ({
        state: silenceStore.state,
        form: {operator: "="}
    }),
    computed: {
        globalMessages() {
            return globalStore.state.messages;
        },
    },
    methods: {
        addLabel() {
            if (this.form.label && this.form.value && this.form.operator) {
                silenceStore.addLabel(this.form.label, [this.form.value, this.form.operator]);
                this.form.label = '';
                this.form.value = '';
                this.form.operator = "=";
            }
        },
        removeLabel(label) {
            delete this.state.labels[label];
        },
        submit() {
            matchers = [];
            for (const [label, value] of Object.entries(this.state.labels)) {
                matchers.push({
                    name: label,
                    value: value[0],
                    isEqual: ["=", "=~"].includes(value[1]),
                    isRegex: ["=~", "!~"].includes(value[1]),
                });
            }

            const body = JSON.stringify({
                matchers: matchers,
                startsAt: this.form.startsAt,
                endsAt: this.form.endsAt,
                duration: this.form.duration,
                createdBy: this.form.createdBy,
                comment: this.form.comment
            });

            const headers = {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value,
            };

            fetch('/proxy/v2/silences', {method: 'POST', headers, body})
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
                this.form = {operator: "="};
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

app.component("data-source-usage", {
    delimiters: ['[[', ']]'],
    props: ["shard", "metric", "max"],
    data: function () {
        return {
            count: 0,
            ready: false,
        };
    },
    mixins: [mixins],
    computed: {
        load: function () {
            return this.count / this.maxAsInt;
        },
        classes: function () {
            if (this.load > 0.9) return "label label-danger";
            if (this.load > 0.7) return "label label-warning";
            if (this.load > 0.5) return "label label-info";
            if (this.count == 0) return "label label-default";
            return "label label-success";
        },
        maxAsInt() {
            return Number.parseInt(this.max);
        },
    },
    template: '#data-source-usage-template',
    mounted() {
        const params = new URLSearchParams({
            metric: this.metric,
        });
        fetch(`/rest/shard/${this.shard}/usages/?${params}`)
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
    addFilterLabel(label, value, operator) {
        const existingLabel = this.state.labels.find(
          (item) =>
            item.label === label &&
            item.value === value &&
            item.operator === operator,
        );
        if (!existingLabel) {
            this.state.labels.push({label, value, operator});
        }
    },
    removeFilterLabel(label, value, operator) {
        const index = this.state.labels.findIndex(
          (item) =>
            item.label === label &&
            item.value === value &&
            item.operator === operator,
        );
        if (index > -1) {
            this.state.labels.splice(index, 1);
        }
    },
    showModal(params=null) {
        // Accept an optional parameter of type object that contains another "matchers" object. This
        // is to allow opening the modal with some matchers already set for filtering.
        //
        // Example call:
        //
        //     showModal({"matchers": {"service": "foo", "project": "bar"}})
        if (
            typeof params === "object" &&
            !Array.isArray(params) &&
            params !== null &&
            params.hasOwnProperty("matchers")
        ) {
            for (const [label, value] of Object.entries(params.matchers)) {
                this.addFilterLabel(label, value);
            }
        }

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
                value: '',
                operator: "="
            },
            store: dataStore
        };
    },
    computed: {
        activeSilences() {
            const silences = this.$root.activeSilences || [];
            if (silences) {
                for (const silence of silences) {
                    silence.matchers.sort((a, b) => a.name.localeCompare(b.name));
                }
            }
            return silences;
        },
        filteredSilences() {
            if (!this.state.labels || this.state.labels.length === 0) {
                return this.activeSilences;
            }

            return this.activeSilences.filter(silence => {
                return this.state.labels.every(filterLabel => {
                    return silence.matchers.some(matcher =>
                        matcher.name === filterLabel.label &&
                        matcher.value === filterLabel.value &&
                        matcher.isEqual === ['=', '=~'].includes(filterLabel.operator) &&
                        matcher.isRegex === ['=~', '!~'].includes(filterLabel.operator)
                    );
                });
            });
        },
        uniqueLabels() {
            const labels = new Set();
            this.filteredSilences.forEach(silence => {
                silence.matchers.forEach(matcher => {
                    labels.add(matcher.name);
                });
            });
            return Array.from(labels).sort();
        },
        filteredOperators() {
            if (!this.form.label) return [];
            const operators = new Set();
            this.filteredSilences.forEach((silence) => {
                silence.matchers.forEach((matcher) => {
                    if (matcher.name === this.form.label) {
                        const op = matcher.isEqual ?
                            (matcher.isRegex ? "=~" : "=") : (matcher.isRegex ? "!~" : "!=");
                        operators.add(op);
                    }
                });
            });
            return ["=", "=~", "!=", "!~"].filter((op) => operators.has(op));
        },
        filteredValues() {
            if (!this.form.label) return [];
            const values = new Set();
            this.filteredSilences.forEach(silence => {
                silence.matchers.forEach(matcher => {
                    if (
                        matcher.name === this.form.label &&
                        (
                            (matcher.isEqual === ["=", "=~"].includes(this.form.operator)) &&
                            (matcher.isRegex === ["=~", "!~"].includes(this.form.operator))
                        )
                    ) {
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
                this.form.operator = "=";
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
        addFilterLabel(label, value, operator) {
            if (label && value && operator) {
                if (
                  !this.state.labels.some(
                    (item) => item.label === label && item.value === value,
                  )
                ) {
                    silenceListStore.addFilterLabel(label, value, operator);
                }
            } else if (this.form.label && this.form.value && this.form.operator) {
                if (
                  !this.state.labels.some(
                    (item) =>
                      item.label === this.form.label &&
                      item.value === this.form.value &&
                      item.value === this.form.operator,
                  )
                ) {
                    silenceListStore.addFilterLabel(
                      this.form.label,
                      this.form.value,
                      this.form.operator,
                    );
                }
            }
            this.form.label = '';
            this.form.value = '';
            this.form.operator = "=";
        },
        removeFilterLabel(label, value, operator) {
            silenceListStore.removeFilterLabel(label, value, operator);
        },
        updateOperatorAndValueOptions() {
            this.updateValueOptions();
            this.form.operator = this.filteredOperators[0];
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
