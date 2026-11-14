document.addEventListener(
    "DOMContentLoaded",
    () => {

        const chartCanvas =
            document.getElementById(
                "accountChart"
            );

        const rangeSelect =
            document.getElementById(
                "accountChartRange"
            );

        const sourceData =
            window.VETMATE_DASHBOARD
                ?.accountChart
            || [];


        if (
            !chartCanvas
            || typeof Chart === "undefined"
        ) {
            return;
        }


        const getThemeColors = () => {
            const styles =
                getComputedStyle(
                    document.documentElement
                );

            return {
                primary:
                    styles
                        .getPropertyValue(
                            "--dashboard-primary"
                        )
                        .trim()
                    || "#894d5b",

                text:
                    styles
                        .getPropertyValue(
                            "--dashboard-text"
                        )
                        .trim()
                    || "#282332",

                muted:
                    styles
                        .getPropertyValue(
                            "--dashboard-muted"
                        )
                        .trim()
                    || "#7e7686",

                border:
                    styles
                        .getPropertyValue(
                            "--dashboard-border"
                        )
                        .trim()
                    || "rgba(80, 60, 80, 0.12)",
            };
        };


        const buildChartData = (
            days
        ) => {
            return sourceData.slice(
                -days
            );
        };


        let colors =
            getThemeColors();

        let currentDays = 7;


        const initialData =
            buildChartData(
                currentDays
            );


        const chart =
            new Chart(
                chartCanvas,
                {
                    type: "line",

                    data: {
                        labels:
                            initialData.map(
                                item =>
                                    item.label
                            ),

                        datasets: [
                            {
                                label:
                                    "Tài khoản mới",

                                data:
                                    initialData.map(
                                        item =>
                                            item.total
                                    ),

                                borderColor:
                                    colors.primary,

                                backgroundColor:
                                    `${colors.primary}22`,

                                borderWidth: 2,

                                pointRadius: 3,

                                pointHoverRadius: 5,

                                tension: 0.35,

                                fill: true,
                            },
                        ],
                    },

                    options: {
                        responsive: true,

                        maintainAspectRatio:
                            false,

                        interaction: {
                            intersect: false,
                            mode: "index",
                        },

                        plugins: {
                            legend: {
                                display: false,
                            },

                            tooltip: {
                                callbacks: {
                                    label: (
                                        context
                                    ) => {
                                        return (
                                            `${context.raw} tài khoản`
                                        );
                                    },
                                },
                            },
                        },

                        scales: {
                            x: {
                                grid: {
                                    display: false,
                                },

                                ticks: {
                                    color:
                                        colors.muted,

                                    maxRotation: 0,
                                },
                            },

                            y: {
                                beginAtZero: true,

                                precision: 0,

                                grid: {
                                    color:
                                        colors.border,
                                },

                                ticks: {
                                    color:
                                        colors.muted,

                                    precision: 0,
                                },
                            },
                        },
                    },
                }
            );


        const updateChart = (
            days
        ) => {
            const data =
                buildChartData(
                    days
                );

            chart.data.labels =
                data.map(
                    item =>
                        item.label
                );

            chart.data.datasets[0].data =
                data.map(
                    item =>
                        item.total
                );

            chart.update();
        };


        rangeSelect?.addEventListener(
            "change",
            () => {
                const days =
                    Number(
                        rangeSelect.value
                    );

                currentDays =
                    days;

                updateChart(
                    days
                );
            }
        );


        /* =================================================
           UPDATE CHART WHEN THEME CHANGES
           ================================================= */

        const observer =
            new MutationObserver(
                () => {
                    colors =
                        getThemeColors();

                    chart.data
                        .datasets[0]
                        .borderColor =
                        colors.primary;

                    chart.data
                        .datasets[0]
                        .backgroundColor =
                        `${colors.primary}22`;

                    chart.options
                        .scales.x.ticks.color =
                        colors.muted;

                    chart.options
                        .scales.y.ticks.color =
                        colors.muted;

                    chart.options
                        .scales.y.grid.color =
                        colors.border;

                    chart.update();
                }
            );


        observer.observe(
            document.documentElement,
            {
                attributes: true,
                attributeFilter: [
                    "data-theme",
                ],
            }
        );

    }
);