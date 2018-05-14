import requests, pyproj, pandas, matplotlib.pyplot as plt

from .func import get_timeseries

class Peilbuis:
    def __init__(self, code, filt, report=False):
        self.report = report
        self.code = code
        self.filt = filt

        lizard_url_loc = 'https://vitens.lizard.net/api/v3/locations/'
        url_loc = '{}?code__icontains={}{}'.format(lizard_url_loc, code, str(filt).zfill(3) )
        if self.report:
            print('GET', url_loc)
        data = requests.get(url_loc).json()['results']

        lat, lon = data[0]['geometry']['coordinates'][1], data[0]['geometry']['coordinates'][0]
        self.lat, self.lon = lat, lon

        p_rd =  pyproj.Proj(init='epsg:28992')
        p_wgs = pyproj.Proj(proj='latlong',datum='WGS84')

        self.x, self.y = pyproj.transform(p_wgs, p_rd, lon, lat)

        dist=0.25
        lizard_url_stn = 'https://vitens.lizard.net/api/v3/groundwaterstations/'
        url_stn = '{}?dist={}&point={},{}'.format(lizard_url_stn, dist, lon, lat)
        if self.report:
            print('GET', url_stn)
        data = requests.get(url_stn).json()['results']

        self.surface_level = data[0]['surface_level']
        for p in data[0]['filters']:
            f = int(p['code'][-3:])
            if f==self.filt:
                data=p

        self.bkf = data['filter_top_level']
        self.okf = data['filter_bottom_level']
        self.uuid_hand  = ''
        self.uuid_diver = ''
        if data['timeseries']!=[]:
            for t in data['timeseries']:
                if t['parameter']=='Handpeiling':
                    self.uuid_hand = t['uuid']
                elif t['parameter']=='Stijghoogte':
                    self.uuid_diver = t['uuid']

    def head_total(self, method='fill'):
        if method=='fill':
            if self.uuid_hand!='' and self.uuid_diver!='':
                df_head = pandas.concat([self.head_diver, self.head_hand],
                                        axis=1)
                df_head['combi']= df_head['diver']
                df_head.loc[pandas.isnull(df_head['diver']), 'combi'] = df_head['hand']
                return df_head['combi']
            elif self.uuid_hand!='':
                return self.head_hand
            elif self.uuid_diver!='':
                return self.head_diver
            else:
                return None
        else:
            return None

    def plot(self, median=True, ax=None, **kwargs):
        head_total = self.head_total()
        if ax is None:
            fig = self._get_figure(**kwargs)
            fig.suptitle('{}, filter {} \n({}, {})'.format(self.code, self.filt, self.bkf, self.okf))
            head_total.plot(style='b-')
            if median:
                plt.plot([head_total.index.min(), head_total.index.max()], 2*[head_total.median()], 'r--')
                plt.legend([head_total.name, 'mediaan'])
            else:
                plt.legend()
            plt.ylabel('Stijghoogte (m+N.A.P.)')
            plt.xlabel('Datum')
            return fig.axes
        else:
            head_total.plot(ax=ax)
            if median:
                ax.plot([head_total.index.min(), head_total.index.max()], 2*[head_total.median()], 'r--')
            return ax

    def _get_figure(self, **kwargs):
        fig = plt.figure(**kwargs)
        return fig

    def __getattr__(self, name):
        if name == 'head_hand':
            self.head_hand = get_timeseries(self.uuid_hand, report=self.report).rename('hand')
            return self.head_hand
        elif name == 'head_diver':
            self.head_diver = get_timeseries(self.uuid_diver, report=self.report).rename('diver')
            return self.head_diver