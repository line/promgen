/*
 * Copyright (c) 2023 LINE Corporation
 * These sources are released under the terms of the MIT license: see LICENSE
 */

var mixins = {
  methods: {
    urlize(value) {
      return linkifyStr(value);
    },
    time(value, fmtstr = "yyyy-MM-dd HH:mm:ss") {
      return luxon.DateTime.fromISO(value).toFormat(fmtstr);
    },
  },
};
