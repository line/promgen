/*
 * Copyright (c) 2023 LINE Corporation
 * These sources are released under the terms of the MIT license: see LICENSE
 */

var mixins = {
  methods: {
    localize(number) {
      return number.toLocaleString();
    },
    percent(number) {
      return (number * 100).toLocaleString() + "%";
    },
    urlize(value) {
      return linkifyStr(value);
    },
  },
};
