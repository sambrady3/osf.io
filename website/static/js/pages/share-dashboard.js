var d3 = require('d3');
var c3 = require('c3');

// function to take 
function getSourcesOneCol(raw_data) {
    var source_data = raw_data['sources']['buckets'];
    var chart_list = [];

    for (i = 0; i < source_data.length; i++){
        var new_item = [];
        new_item.push(source_data[i]['key']);
        new_item.push(source_data[i]['doc_count']);
        chart_list.push(new_item);
    }

    return chart_list;
}

function getSourcesManyCol(raw_data) {
    var source_data = raw_data['sources']['buckets'];
    var col_names = ['x'];
    var col_counts = ['count'];
    var main_list = [];

    for (i = 0; i < source_data.length; i++){
        var source_info = [];
        col_names.push(source_data[i]['key']);
        col_counts.push(source_data[i]['doc_count']);
    }

    main_list.push(col_names);
    main_list.push(col_counts);

    return main_list;
}

function getDateChunks(raw_data) {
    var date_data = raw_data['date_chunks']['buckets'];

    var main_list = [];
    var date_names = ['x'];
    
    for (i = 0; i < date_data.length; i++){
        var source_info = [];
        col_names.push(source_data[i]['key']);
        col_counts.push(source_data[i]['doc_count']);
    }
}

$.ajax({
    url: '../api/v1/share/stats/',
    method: 'get'
}).done(function(elastic_data) {

    var chart_manycol = getSourcesManyCol(elastic_data);
    var chart1 = c3.generate({
        bindto: '#shareDashboard1',
        data: {
            x : 'x',
            columns : chart_manycol,
            type: 'bar'
        },
        axis: {
            x: {
                type: 'category' // this needed to load string x value
            }
        }
    });

    var chart2 = c3.generate({
        bindto: '#shareDashboard2',
        data: {
            columns: getSourcesOneCol(elastic_data),
            type : 'donut',
        },
        donut: {
            title: "SHARE Providers"
        }
    });

    var chart3 = c3.generate({
        bindto: '#shareDashboard3',
        data: {
            x: 'x',
            columns: [
                ['x', '1/15', '2/15', '3/15', '4/15', '5/15', '6/15'],
                ['arxiv', 30, 200, 100, 400, 150, 250],
                ['figshare', 130, 300, 200, 300, 250, 450]
            ]
        },
        axis: {
            x: {
                type: 'category' // this needed to load string x value
            }
        }
    });

    var chart_onecol = getSourcesOneCol(elastic_data);
    var chart4 = c3.generate({
        bindto: '#shareDashboard4',
        data: {
            columns : chart_onecol,
            type: 'bar'
        }
    });

})
