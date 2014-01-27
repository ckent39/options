#!/usr/bin/env python

import numpy as np
from scipy import interpolate
from pandas import *
from datetime import *

class zeroCurve:

	def __init__(self):
		self.zero_curve = None
		self.__h15Url = 'http://www.federalreserve.gov/datadownload/Output.aspx?rel=H15&series=bf17364827e38702b42a58cf8eaa3f78&lastObs=&from=&to=&filetype=csv&label=include&layout=seriescolumn&type=package'

		self.__tenors = [1, 3, 6, 12, 24, 36, 60, 84, 120, 240, 360]
		self.__cash_names = ["1m", "3m", "6m", "12m"]
 		self.__cash_tenors = [1, 3, 6, 12]
		self.__bond_names = ["24m", "36m", "60m", "84m", "120m", "240m", "360m"]
		self.__bond_tenors = [24, 36, 60, 84, 120, 240, 360]
		self.__zero_times = map(lambda x: x/12.0, [1, 3]+[i for i in xrange(6, 361, 6)])
		self.__start_date = datetime(2002, 1, 1)

	def load_curve(self):
		df = read_csv(self.__h15Url, skiprows=70)
		df.columns = ['date'] + [str(tenor)+"m" for tenor in self.__tenors]
		df['date'] = map(lambda x: datetime.strptime(x, '%Y-%m-%d'), df['date'])
		df = df.set_index("date")
		filter_keep = list(df['1m']!='ND')
		df = df[filter_keep][self.__start_date:]
		t360_nD = list(df["360m"]=='ND')
		df['360m'][t360_nD] = df['240m'][t360_nD]
		df = df.astype(float)/100
	
		return df

	def get_zeros(self, cash_names, bond_names, cash_rates, bond_rates, cash_tenors, bond_tenors):
		df_all = 1/(cash_rates*cash_tenors/12+1)
		md = np.append(df_all[['6m', '12m']].values, np.arange(18,361,6))
		dv = md.cumsum() / 2
		fe_bonds = np.array([2*(1-md[i-1])/md[0:i].sum() for i in xrange(1,3)])
		bond_times = np.arange(6, 361, 6)
		by = interpolate.interp1d(np.append([6,12], bond_tenors),np.append(fe_bonds, bond_rates), kind=1)(bond_times)
		
		for i in xrange(2, len(by)):
			md[i] = (1 - dv[i-1] * by[i])/(1 + by[i] * dv[i-1])
			dv[i] = md[0:(i+1)].sum() / 2
		
		all_times = np.append(cash_tenors,bond_times[2:])
		all_factr = np.append(df_all.values, md[2:])
		
		return -12*np.log(all_factr)/all_times

	def strip_all(self, df):
		zeros = map(lambda x: (x[0], self.get_zeros(self.__cash_names, self.__bond_names, x[1][self.__cash_names], x[1][self.__bond_names], self.__cash_tenors, self.__bond_tenors)), df.iterrows())
		df = DataFrame.from_items(zeros, orient="index", columns=["USD"+str(j) for j in self.__cash_tenors+[i for i in xrange(18,361,6)]])
		
		return df

	def zero_data(self):
		df = self.load_curve()
		self.zero_curve = self.strip_all(df)

	def zero_rate(self, asof, tenor):
		zero_rates = self.zero_curve[self.zero_curve.index < asof][-1:]
		return float(interpolate.interp1d(x=np.array(self.__zero_times), y=zero_rates.values[0], kind="linear")(tenor))