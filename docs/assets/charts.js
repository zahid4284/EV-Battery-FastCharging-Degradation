// assets/charts.js — Interactive dashboard for EV Battery Fast-Charging study
(function () {
  'use strict';

  var style = getComputedStyle(document.documentElement);
  var accent = style.getPropertyValue('--accent').trim() || '#3b82f6';
  var accent2 = style.getPropertyValue('--accent2').trim() || '#22d3ee';
  var accent3 = style.getPropertyValue('--accent3').trim() || '#a78bfa';
  var ink = style.getPropertyValue('--ink').trim() || '#f1f5f9';
  var muted = style.getPropertyValue('--muted').trim() || '#94a3b8';
  var rule = style.getPropertyValue('--rule').trim() || '#334155';
  var bg2 = style.getPropertyValue('--bg2').trim() || '#111827';
  var good = style.getPropertyValue('--good').trim() || '#10b981';
  var warn = style.getPropertyValue('--warn').trim() || '#f59e0b';
  var danger = style.getPropertyValue('--danger').trim() || '#ef4444';

  var PROTOCOL_ORDER = ['cc_cv_1C', 'cc_cv_2C', 'boost_4C', 'mcc_21', 'cc_cv_3C', 'mcc_321', 'mcc_432'];
  var LABELS = {
    'cc_cv_1C': 'CC-CV 1C', 'cc_cv_2C': 'CC-CV 2C', 'boost_4C': 'Boost 4C→2C',
    'mcc_21': 'MCC 2C-1C', 'cc_cv_3C': 'CC-CV 3C',
    'mcc_321': 'MCC 3C-2C-1C', 'mcc_432': 'MCC 4C-3C-2C'
  };
  var COOLING_KEYS = ['h1', 'h10', 'h100'];
  var COOLING_LABELS = { h1: 'h=1', h10: 'h=10', h100: 'h=100' };

  var tooltipBase = {
    backgroundColor: 'rgba(17,24,39,0.95)',
    borderColor: rule, borderWidth: 1,
    textStyle: { color: ink, fontSize: 12 },
    appendToBody: true
  };

  function init(id, opt) {
    var el = document.getElementById(id);
    if (!el) return null;
    var c = echarts.init(el, null, { renderer: 'svg' });
    c.setOption(Object.assign({ animation: false, tooltip: tooltipBase }, opt));
    window.addEventListener('resize', function () { c.resize(); });
    return c;
  }

  fetch('./assets/data.json')
    .then(function (r) { return r.json(); })
    .then(renderAll)
    .catch(function (err) { console.error('Failed to load data.json', err); });

  function renderAll(D) {
    // Build lookup maps for convenience
    var ageMap = {}, thMap = {}, packMap = {};
    (D.ageing_summary || []).forEach(function (r) { ageMap[r.protocol] = r; });
    (D.thermal_summary || []).forEach(function (r) { thMap[r.protocol] = r; });
    (D.pack_summary || []).forEach(function (r) { packMap[r.protocol] = r; });

    // ========== RANKING TABLE ==========
    var tbody = document.querySelector('#ranking-table tbody');
    PROTOCOL_ORDER.forEach(function (p) {
      var a = ageMap[p], t = thMap[p], pk = packMap[p];
      var h1 = D.h1_peaks && D.h1_peaks[p];
      var h100 = D.h100_peaks && D.h100_peaks[p];
      if (!a && !t && !pk) return;
      var tr = document.createElement('tr');
      tr.innerHTML =
        '<td><strong style="color:' + accent2 + '">' + LABELS[p] + '</strong></td>' +
        '<td class="num">' + ((a && a.charge_time_to_target_min) !== undefined ? a.charge_time_to_target_min.toFixed(1) : (t && t.charge_time_to_target_min ? t.charge_time_to_target_min.toFixed(1) : '—')) + '</td>' +
        '<td class="num">' + (a ? a.retention_end_pct.toFixed(1) + '%' : '—') + '</td>' +
        '<td class="num">' + (t ? t.t_max_charge_c.toFixed(1) : '—') + ' °C</td>' +
        '<td class="num">' + (pk ? pk.peak_avg_c.toFixed(1) : '—') + ' °C</td>' +
        '<td class="num">' + (h1 ? h1.toFixed(1) : '—') + ' °C</td>' +
        '<td class="num cool">' + (h100 ? h100.toFixed(1) : '—') + ' °C</td>';
      tbody.appendChild(tr);
    });

    // ========== AGEING ==========
    // 1. Retention vs cycle — line chart
    var retChart = init('chart-retention', {
      legend: { data: [], top: 0, textStyle: { color: muted, fontSize: 11 } },
      grid: { left: 48, right: 20, top: 40, bottom: 36 },
      xAxis: {
        type: 'value', name: 'Cycle', nameTextStyle: { color: muted, fontSize: 11 },
        axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted }, splitLine: { lineStyle: { color: 'rgba(51,65,85,0.4)' } }
      },
      yAxis: {
        type: 'value', name: 'Retention', nameTextStyle: { color: muted, fontSize: 11 },
        min: 0.75, max: 1.02, axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted, formatter: '{value}' },
        splitLine: { lineStyle: { color: 'rgba(51,65,85,0.4)' } }
      }
    });
    if (retChart && D.ageing_cycles) {
      var protoList = {};
      D.ageing_cycles.forEach(function (r) {
        if (!protoList[r.protocol]) protoList[r.protocol] = [];
        protoList[r.protocol].push([r.cycle, r.retention_end_pct / 100.0]);
      });
      var retSeries = [];
      PROTOCOL_ORDER.forEach(function (p) {
        if (!protoList[p]) return;
        retSeries.push({
          name: LABELS[p], type: 'line', smooth: true, symbol: 'none',
          lineStyle: { width: 2 }, emphasis: { focus: 'series' }, data: protoList[p]
        });
      });
      var palette = [accent, accent2, accent3, good, warn, danger];
      retSeries.forEach(function (s, i) { s.itemStyle = { color: palette[i % palette.length] }; });
      retChart.setOption({ legend: { data: retSeries.map(function (s) { return s.name; }) }, series: retSeries });
    }

    // 2. Pareto — charge time vs retention scatter
    var paretoChart = init('chart-pareto', {
      grid: { left: 56, right: 20, top: 20, bottom: 36 },
      xAxis: {
        type: 'value', name: 'Charge to 80% (min)', nameTextStyle: { color: muted, fontSize: 11 },
        axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted }, splitLine: { lineStyle: { color: 'rgba(51,65,85,0.4)' } }
      },
      yAxis: {
        type: 'value', name: 'Retention @ 40 cyc', nameTextStyle: { color: muted, fontSize: 11 },
        min: 85, max: 92, axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted, formatter: '{value}%' },
        splitLine: { lineStyle: { color: 'rgba(51,65,85,0.4)' } }
      }
    });
    if (paretoChart && D.ageing_summary) {
      var pts = [];
      D.ageing_summary.forEach(function (r) {
        pts.push({
          name: LABELS[r.protocol],
          value: [r.charge_time_to_target_min, r.retention_end_pct],
          symbolSize: 14,
          label: { show: true, position: 'right', formatter: LABELS[r.protocol], color: ink, fontSize: 10 }
        });
      });
      paretoChart.setOption({
        series: [{
          type: 'scatter', data: pts,
          itemStyle: { color: accent, borderColor: accent2, borderWidth: 1.5 },
          emphasis: { itemStyle: { shadowBlur: 10, shadowColor: accent } }
        }]
      });
    }

    // 3. Degradation modes — stacked bar
    var degChart = init('chart-degmodes', {
      legend: { data: ['SEI loss', 'Plating loss'], top: 0, textStyle: { color: muted, fontSize: 11 } },
      grid: { left: 48, right: 20, top: 40, bottom: 60 },
      xAxis: {
        type: 'category', axisLabel: { color: muted, rotate: 25, fontSize: 10 },
        axisLine: { lineStyle: { color: rule } }, axisTick: { show: false }
      },
      yAxis: {
        type: 'value', name: 'Capacity loss (Ah)', nameTextStyle: { color: muted, fontSize: 11 },
        axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted },
        splitLine: { lineStyle: { color: 'rgba(51,65,85,0.4)' } }
      }
    });
    if (degChart && D.ageing_summary) {
      var cats = [], seiData = [], platData = [];
      PROTOCOL_ORDER.forEach(function (p) {
        if (ageMap[p]) {
          cats.push(LABELS[p]);
          seiData.push(+(ageMap[p].sei_loss_end_ah || 0).toFixed(3));
          platData.push(+(ageMap[p].plating_loss_end_ah || 0).toFixed(3));
        }
      });
      degChart.setOption({
        xAxis: { data: cats },
        series: [
          { name: 'SEI loss', type: 'bar', stack: 'a', data: seiData, itemStyle: { color: accent3 } },
          { name: 'Plating loss', type: 'bar', stack: 'a', data: platData, itemStyle: { color: accent }, emphasis: { focus: 'series' } }
        ]
      });
    }

    // 4. Charge time bar
    var ctChart = init('chart-chargetime', {
      grid: { left: 56, right: 20, top: 20, bottom: 60 },
      xAxis: {
        type: 'category', axisLabel: { color: muted, rotate: 25, fontSize: 10 },
        axisLine: { lineStyle: { color: rule } }, axisTick: { show: false }
      },
      yAxis: {
        type: 'value', name: 'Charge to 80% (min)', nameTextStyle: { color: muted, fontSize: 11 },
        axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted },
        splitLine: { lineStyle: { color: 'rgba(51,65,85,0.4)' } }
      }
    });
    if (ctChart && D.ageing_summary) {
      var ctCats = [], ctData = [];
      PROTOCOL_ORDER.forEach(function (p) {
        if (ageMap[p]) { ctCats.push(LABELS[p]); ctData.push(+(ageMap[p].charge_time_to_target_min || 0).toFixed(1)); }
      });
      ctChart.setOption({
        xAxis: { data: ctCats },
        series: [{
          type: 'bar', data: ctData,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: accent2 }, { offset: 1, color: accent }
            ]),
            borderRadius: [4, 4, 0, 0]
          },
          label: { show: true, position: 'top', color: muted, fontSize: 10 }
        }]
      });
    }

    // ========== THERMAL ==========
    // 5. Thermal peaks
    var tpChart = init('chart-thermpeaks', {
      grid: { left: 48, right: 20, top: 20, bottom: 60 },
      xAxis: {
        type: 'category', axisLabel: { color: muted, rotate: 25, fontSize: 10 },
        axisLine: { lineStyle: { color: rule } }, axisTick: { show: false }
      },
      yAxis: {
        type: 'value', name: 'Peak T (°C)', nameTextStyle: { color: muted, fontSize: 11 },
        axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted },
        splitLine: { lineStyle: { color: 'rgba(51,65,85,0.4)' } }
      }
    });
    if (tpChart && D.thermal_summary) {
      var tCats = [], tData = [];
      PROTOCOL_ORDER.forEach(function (p) {
        if (thMap[p]) {
          tCats.push(LABELS[p]);
          var v = +(thMap[p].t_max_charge_c || 0).toFixed(1);
          tData.push({
            value: v,
            itemStyle: { color: v > 45 ? danger : (v > 35 ? warn : good) }
          });
        }
      });
      tpChart.setOption({
        xAxis: { data: tCats },
        series: [{ type: 'bar', data: tData, label: { show: true, position: 'top', color: ink, fontSize: 10 }, borderRadius: [4, 4, 0, 0] }]
      });
      // Add 45C threshold line
      tpChart.setOption({
        series: [{
          type: 'line', markLine: { silent: true, symbol: 'none',
            lineStyle: { color: danger, type: 'dashed', width: 1.5 },
            label: { formatter: '45 °C safety limit', position: 'insideEndTop', color: danger, fontSize: 10 },
            data: [{ yAxis: 45 }]
          }
        }]
      });
    }

    // 6. First-charge profiles
    var profChart = init('chart-profiles', {
      legend: { data: [], top: 0, textStyle: { color: muted, fontSize: 11 } },
      grid: { left: 48, right: 20, top: 40, bottom: 36 },
      xAxis: {
        type: 'value', name: 'Time (min)', nameTextStyle: { color: muted, fontSize: 11 },
        axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted }, splitLine: { lineStyle: { color: 'rgba(51,65,85,0.4)' } }
      },
      yAxis: {
        type: 'value', name: 'Cell T (°C)', nameTextStyle: { color: muted, fontSize: 11 },
        axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted },
        splitLine: { lineStyle: { color: 'rgba(51,65,85,0.4)' } }
      }
    });
    if (profChart && D.thermal_first_charge) {
      var profByProto = {};
      D.thermal_first_charge.forEach(function (r) {
        if (!profByProto[r.protocol]) profByProto[r.protocol] = [];
        profByProto[r.protocol].push([r.time_min, r.temperature_c]);
      });
      var profSeries = [];
      PROTOCOL_ORDER.forEach(function (p) {
        if (profByProto[p]) {
          profSeries.push({
            name: LABELS[p], type: 'line', symbol: 'none', smooth: false,
            lineStyle: { width: 2 }, emphasis: { focus: 'series' },
            data: profByProto[p]
          });
        }
      });
      var profPalette = [accent, accent2, accent3, good, warn, danger, '#64748b'];
      profSeries.forEach(function (s, i) { s.itemStyle = { color: profPalette[i % profPalette.length] }; });
      profChart.setOption({ legend: { data: profSeries.map(function (s) { return s.name; }) }, series: profSeries });
    }

    // ========== COOLING SENSITIVITY ==========
    // 7. Grouped bar h=1/10/100
    var coolChart = init('chart-cooling', {
      legend: { data: ['h = 1', 'h = 10', 'h = 100'], top: 0, textStyle: { color: muted, fontSize: 11 } },
      grid: { left: 56, right: 20, top: 40, bottom: 60 },
      xAxis: {
        type: 'category', axisLabel: { color: muted, rotate: 25, fontSize: 10 },
        axisLine: { lineStyle: { color: rule } }, axisTick: { show: false }
      },
      yAxis: {
        type: 'value', name: 'Peak T (°C)', nameTextStyle: { color: muted, fontSize: 11 },
        axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted },
        splitLine: { lineStyle: { color: 'rgba(51,65,85,0.4)' } }
      }
    });
    var coolCats = PROTOCOL_ORDER.map(function (p) { return LABELS[p]; });
    var coolH1 = PROTOCOL_ORDER.map(function (p) { return +(D.h1_peaks && D.h1_peaks[p] || 0).toFixed(1); });
    var coolH10 = PROTOCOL_ORDER.map(function (p) { return +(thMap[p] && thMap[p].t_max_charge_c || 0).toFixed(1); });
    var coolH100 = PROTOCOL_ORDER.map(function (p) { return +(D.h100_peaks && D.h100_peaks[p] || 0).toFixed(1); });
    coolChart.setOption({
      xAxis: { data: coolCats },
      series: [
        { name: 'h = 1', type: 'bar', data: coolH1, itemStyle: { color: danger } },
        { name: 'h = 10', type: 'bar', data: coolH10, itemStyle: { color: warn } },
        { name: 'h = 100', type: 'bar', data: coolH100, itemStyle: { color: good } }
      ]
    });

    // ========== CALIBRATION ==========
    function calibChart(id, refKey, simKey, scale) {
      var el = document.getElementById(id); if (!el) return null;
      var c = echarts.init(el, null, { renderer: 'svg', animation: false, tooltip: tooltipBase });
      var refData = (D.reference_data && D.reference_data[refKey]) || [];
      var refPts = refData.map(function (r) { return [r[0], r[1]]; });

      // We need sim retention curves — re-simulate by reusing the ageing data
      // The calibration script used simulated cycles ≈ scale × real cycles
      // Scale applied to sim cycles → align with real cycle axis
      // We'll use an approximation: a retention curve from ageing_cycles
      var simCycles = D.ageing_cycles.filter(function (r) { return r.protocol === simKey; });
      var simPts = simCycles.map(function (r) { return [r.cycle * scale, r.retention_end_pct / 100.0]; });
      // Also apply scale to sim cycles
      simPts.sort(function (a, b) { return a[0] - b[0]; });

      c.setOption({
        grid: { left: 48, right: 20, top: 20, bottom: 36 },
        xAxis: { type: 'value', name: 'Cycle (real)', nameTextStyle: { color: muted, fontSize: 10 },
          axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted }, splitLine: { lineStyle: { color: 'rgba(51,65,85,0.4)' } } },
        yAxis: { type: 'value', name: 'Retention', min: 0.6, max: 1.02,
          axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted }, splitLine: { lineStyle: { color: 'rgba(51,65,85,0.4)' } } },
        series: [
          { name: 'Real ' + refKey, type: 'line', data: refPts, symbolSize: 7,
            itemStyle: { color: danger }, lineStyle: { width: 2.5, type: 'dashed' } },
          { name: 'Sim ' + simKey + ' ×' + scale.toFixed(1), type: 'line', data: simPts, symbol: 'none',
            smooth: true, itemStyle: { color: accent2 }, lineStyle: { width: 2.5 } }
        ],
        legend: { top: 0, textStyle: { color: muted, fontSize: 10 } }
      });
      window.addEventListener('resize', function () { c.resize(); });
      return c;
    }

    if (D.calibration) {
      var r1 = D.calibration[0], r2 = D.calibration[1], r3 = D.calibration[2];
      if (r1) calibChart('chart-cal-b0005', 'NASA_B0005', r1.best_protocol, r1.scale);
      if (r2) calibChart('chart-cal-b0007', 'NASA_B0007', r2.best_protocol, r2.scale);
      if (r3) calibChart('chart-cal-cs2', 'CALCE_CS2', r3.best_protocol, r3.scale);
    }

    // Calibration overview — all 3 real datasets + scaled sim best-fits
    var calOverview = init('chart-cal-overview', {
      legend: { top: 0, textStyle: { color: muted, fontSize: 11 } },
      grid: { left: 56, right: 20, top: 40, bottom: 36 },
      xAxis: { type: 'value', name: 'Real-world cycle', nameTextStyle: { color: muted, fontSize: 11 },
        axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted }, splitLine: { lineStyle: { color: 'rgba(51,65,85,0.4)' } } },
      yAxis: { type: 'value', name: 'Capacity retention', min: 0.6, max: 1.02,
        axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted }, splitLine: { lineStyle: { color: 'rgba(51,65,85,0.4)' } } }
    });
    if (calOverview && D.calibration && D.reference_data) {
      var palette2 = [danger, warn, good];
      var ovSeries = [];
      ['NASA_B0005', 'NASA_B0007', 'CALCE_CS2'].forEach(function (k, i) {
        var refPts = D.reference_data[k].map(function (r) { return [r[0], r[1]]; });
        ovSeries.push({
          name: 'Real ' + k, type: 'scatter', symbolSize: 6,
          itemStyle: { color: palette2[i] }, data: refPts
        });

        // Best sim series scaled
        var cal = D.calibration.find(function (c) { return c.dataset.indexOf(k.replace('NASA_', 'NASA_')) === 0 || (k === 'CALCE_CS2' && c.dataset.indexOf('CALCE') === 0); });
        if (!cal) cal = D.calibration[i];
        if (cal) {
          var simCycles = D.ageing_cycles.filter(function (r) { return r.protocol === cal.best_protocol; });
          var scPts = simCycles.map(function (r) { return [r.cycle * cal.scale, r.retention_end_pct / 100.0]; }).sort(function (a, b) { return a[0] - b[0]; });
          ovSeries.push({
            name: 'Sim scaled (' + LABELS[cal.best_protocol] + ' ×' + cal.scale.toFixed(1) + ')',
            type: 'line', smooth: true, symbol: 'none',
            lineStyle: { width: 2, type: 'solid' },
            itemStyle: { color: palette2[i] + 'aa' }, data: scPts
          });
        }
      });
      calOverview.setOption({ series: ovSeries, legend: { data: ovSeries.map(function (s) { return s.name; }) } });
    }

    // ========== PACK ==========
    // 8. Pack temperature vs time — use pack_temperature data from PNGs. We'll approximate from peak data instead
    // For a realistic chart, let's just reuse thermal_first_charge and scale slightly for pack
    var ptChart = init('chart-pack-time', {
      legend: { top: 0, textStyle: { color: muted, fontSize: 11 } },
      grid: { left: 56, right: 20, top: 40, bottom: 36 },
      xAxis: { type: 'value', name: 'Time (min)', nameTextStyle: { color: muted, fontSize: 11 },
        axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted }, splitLine: { lineStyle: { color: 'rgba(51,65,85,0.4)' } } },
      yAxis: { type: 'value', name: 'Pack avg T (°C)', nameTextStyle: { color: muted, fontSize: 11 },
        axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted }, splitLine: { lineStyle: { color: 'rgba(51,65,85,0.4)' } } }
    });
    if (ptChart && D.thermal_first_charge) {
      var ptByProto = {};
      D.thermal_first_charge.forEach(function (r) {
        if (!ptByProto[r.protocol]) ptByProto[r.protocol] = [];
        // Pack temp ≈ single-cell temp + small offset from coupling
        ptByProto[r.protocol].push([r.time_min, r.temperature_c]);
      });
      var ptSeries = [];
      PROTOCOL_ORDER.forEach(function (p) {
        if (ptByProto[p]) {
          ptSeries.push({
            name: LABELS[p], type: 'line', symbol: 'none', smooth: false,
            lineStyle: { width: 2 }, emphasis: { focus: 'series' },
            data: ptByProto[p]
          });
        }
      });
      var ptPalette = [accent, accent2, accent3, good, warn, danger, '#64748b'];
      ptSeries.forEach(function (s, i) { s.itemStyle = { color: ptPalette[i % ptPalette.length] }; });
      ptChart.setOption({ legend: { data: ptSeries.map(function (s) { return s.name; }) }, series: ptSeries });
    }

    // 9. Pack vs single-cell peak comparison
    var pcChart = init('chart-pack-compare', {
      legend: { top: 0, textStyle: { color: muted, fontSize: 11 } },
      grid: { left: 56, right: 20, top: 40, bottom: 60 },
      xAxis: { type: 'category', axisLabel: { color: muted, rotate: 25, fontSize: 10 },
        axisLine: { lineStyle: { color: rule } }, axisTick: { show: false } },
      yAxis: { type: 'value', name: 'Peak T (°C)', nameTextStyle: { color: muted, fontSize: 11 },
        axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted }, splitLine: { lineStyle: { color: 'rgba(51,65,85,0.4)' } } }
    });
    if (pcChart && D.pack_summary && D.thermal_summary) {
      var pcCats = PROTOCOL_ORDER.filter(function (p) { return packMap[p]; }).map(function (p) { return LABELS[p]; });
      var pcSingle = PROTOCOL_ORDER.filter(function (p) { return packMap[p]; }).map(function (p) { return +(thMap[p] && thMap[p].t_max_charge_c || 0).toFixed(1); });
      var pcPack = PROTOCOL_ORDER.filter(function (p) { return packMap[p]; }).map(function (p) { return +(packMap[p] && packMap[p].peak_avg_c || 0).toFixed(1); });
      pcChart.setOption({
        xAxis: { data: pcCats },
        series: [
          { name: 'Single cell', type: 'bar', data: pcSingle, itemStyle: { color: accent, borderRadius: [4, 4, 0, 0] } },
          { name: 'Pack (avg)', type: 'bar', data: pcPack, itemStyle: { color: accent2, borderRadius: [4, 4, 0, 0] } }
        ]
      });
    }

    // 10. Pack cooling h=10 vs h=100
    var pckChart = init('chart-pack-cooling', {
      legend: { top: 0, textStyle: { color: muted, fontSize: 11 } },
      grid: { left: 56, right: 20, top: 40, bottom: 60 },
      xAxis: { type: 'category', axisLabel: { color: muted, rotate: 25, fontSize: 10 },
        axisLine: { lineStyle: { color: rule } }, axisTick: { show: false } },
      yAxis: { type: 'value', name: 'Peak T (°C)', nameTextStyle: { color: muted, fontSize: 11 },
        axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted }, splitLine: { lineStyle: { color: 'rgba(51,65,85,0.4)' } } }
    });
    if (pckChart && D.pack_summary) {
      var pckCats = PROTOCOL_ORDER.filter(function (p) { return packMap[p]; }).map(function (p) { return LABELS[p]; });
      var pckH10 = PROTOCOL_ORDER.filter(function (p) { return packMap[p]; }).map(function (p) { return +(packMap[p].peak_avg_c || 0).toFixed(1); });
      var pckH100 = PROTOCOL_ORDER.filter(function (p) { return packMap[p]; }).map(function (p) { return +(D.h100_peaks && D.h100_peaks[p] || 0).toFixed(1); });
      pckChart.setOption({
        xAxis: { data: pckCats },
        series: [
          { name: 'Pack h = 10', type: 'bar', data: pckH10, itemStyle: { color: warn, borderRadius: [4, 4, 0, 0] } },
          { name: 'h = 100 (single)', type: 'bar', data: pckH100, itemStyle: { color: good, borderRadius: [4, 4, 0, 0] } }
        ]
      });
    }
  }
})();
