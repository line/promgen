// https://esbuild.github.io/plugins/#using-plugins

const esbuild = require("esbuild");
const vue3Plugin = require("esbuild-plugin-vue3");

const myPlugin = {
  name: "my-plugin",
  setup(build) {
    build.onResolve({ filter: /^vue$/ }, (args) => ({
      path: args.path,
      namespace: "my-plugin",
    }));

    build.onLoad({ filter: /.*/, namespace: "my-plugin" }, () => ({
      contents: "module.exports = Vue",
    }));
  },
};
(async () => {
  await esbuild.build({
    entryPoints: ["./src/main.js"],
    bundle: true,
    outdir: "../promgen/static/primevue",
    logLevel: "info",
    loader: {
      ".woff2": "dataurl",
    },
    plugins: [myPlugin, vue3Plugin()],
    minify: true,
  });
})();
