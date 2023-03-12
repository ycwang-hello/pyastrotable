# -*- coding: utf-8 -*-
"""
Created on Sat Jul 30 2022

@author: Yuchen Wang

Built-in matchers.
"""

import numpy as np
from astrotable.utils import find_idx
from astropy.coordinates import SkyCoord
import astropy.units as u
from astropy.units import UnitTypeError

class ExactMatcher():
    def __init__(self, value, value1):
        '''
        Used to match `astrotable.table.Data` objects `data1` to `data`.
        Match records with exact values.
        This should be passed to method `data.match()`.
        See `help(data.match)`.

        Parameters
        ----------
        value : str or Iterable
            Specify values for `data` used to match catalogs. Possible inputs are:
            - str, name of the field used for matching.
            - Iterable, values for `data`. `len(value)` should be equal to `len(data)`.
        value1 : str or Iterable
            Specify values for `data1` used to match catalogs. Possible inputs are:
            - str, name of the field used for matching.
            - Iterable, values for `data1`. `len(value1)` should be equal to `len(data1)`.
        '''
        self.value = value
        self.value1 = value1
    
    def get_values(self, data, data1, verbose=True):
        if type(self.value) is str:
            self.value = data.t[self.value]
        if type(self.value1) is str:
            self.value1 = data1.t[self.value1]
        missings = [] # whether the coord is missing
        not_missing_ids = [] # the indices of those that are not missing
        for valuei, datai in [[self.value, data], [self.value1, data1]]:
            if datai.t.masked:
                missingi = valuei.mask
            else:
                missingi = np.full(len(datai), False)
            not_missing_idi = np.arange(len(datai), dtype=int)[~missingi]
            missings.append(missingi)
            not_missing_ids.append(not_missing_idi)
        
        self.missing, self.missing1 = missings
        self.not_missing_id, self.not_missing_id1 = not_missing_ids
    
    def match(self):
        l = len(self.missing)
        idx = np.full(self.missing.shape, -l-1)
        matched = np.full(self.missing.shape, False)
        idx_nm, matched_nm = find_idx(self.value1[~self.missing1], self.value[~self.missing])
        matched[~self.missing] = matched_nm
        idx[matched] = self.not_missing_id1[idx_nm[matched_nm]]
        return idx, matched
    
    def __repr__(self):
        return f"ExactMatcher('{self.value.name}', '{self.value1.name}')"


class SkyMatcher():
    def __init__(self, thres=1, coord=None, coord1=None, unit=u.deg, unit1=u.deg):
        '''
        Used to match `astrotable.table.Data` objects `data1` to `data`.
        Match records with nearest coordinates.
        This should be passed to method `data.match()`.
        See `help(data.match)`.

        Parameters
        ----------
        thres : number, optional
            Threshold in arcsec. The default is 1.
        coord : str or astropy.coordinates.SkyCoord, optional
            Specify coordinate for the base data. Possible inputs are:
            - astropy.coordinates.SkyCoord (recommended), the coordinate object.
            - str, should be like 'RA-DEC', which specifies the column name for RA and Dec.
            - None (default), will try ['ra', 'RA'] and ['DEC', 'Dec', 'dec'].
            The default is None.
        coord1 : str or astropy.coordinates.SkyCoord, optional
            Specify coordinate for the matched data. Possible inputs are:
            - astropy.coordinates.SkyCoord (recommended), the coordinate object.
            - str, should be like 'RA-DEC', which specifies the column name for RA and Dec.
            - None (default), will try ['ra', 'RA'] and ['DEC', 'Dec', 'dec'].
            The default is None.
        unit : astropy.units.core.Unit or list/tuple/array of it
            If astropy.coordinates.SkyCoord object is not given for coord, 
            this is used to specify the unit of coord.
            The default is astropy.units.deg.
        unit1 : astropy.units.core.Unit or list/tuple/array of it
            If astropy.coordinates.SkyCoord object is not given for coord1, 
            this is used to specify the unit of coord1.
            The default is astropy.units.deg.
           
        Notes
        -----
        The data columns for RA, Dec may already have units (e.g. ``data.t['RA'].unit``).
        In this case, any input for ``unit`` or ``unit1`` is ignored, and the units recorded
        in the columns are used.
        '''
        self.thres = thres
        self.coord = coord
        self.coord1 = coord1
        self.unit = unit
        self.unit1 = unit1
    
    def get_values(self, data, data1, verbose=True):
        # TODO: this method has not been debugged!
        # USE WITH CAUTION!
        ra_names = np.array(['ra', 'RA'])
        dec_names = np.array(['DEC', 'Dec', 'dec'])
        coords = []
        missings = [] # whether the coord is missing
        not_missing_ids = [] # the indices of those that are not missing
        for coordi, datai, uniti in [[self.coord, data, self.unit], [self.coord1, data1, self.unit1]]:
            if coordi is None or isinstance(coordi, str):
                if coordi is None: # auto decide ra, dec
                    found_ra = np.isin(ra_names, datai.colnames)
                    if not np.any(found_ra):
                        raise KeyError(f'RA for {datai.name} not found.')
                    self.ra_name = ra_names[np.where(found_ra)][0]
                    ra = datai.t[self.ra_name]
    
                    found_dec = np.isin(dec_names, datai.colnames)
                    if not np.any(found_dec):
                        raise KeyError(f'Dec for {datai.name} not found.')
                    self.dec_name = dec_names[np.where(found_dec)][0]
                    dec = datai.t[self.dec_name]
                    
                    if verbose: print(f"[SkyMatcher] Data {datai.name}: found RA name '{self.ra_name}' and Dec name '{self.dec_name}'.")
            
                else: # type(coordi) is str:
                    self.ra_name, self.dec_name = coordi.split('-')
                    ra = datai.t[self.ra_name]
                    dec = datai.t[self.dec_name]
                
                # check missing values for ra and dec
                if datai.t.masked:
                    missingi = ra.mask | dec.mask
                else:
                    missingi = np.full(len(datai), False)
                not_missing_idi = np.arange(len(datai), dtype=int)[~missingi]
                
                try:
                    coordi = SkyCoord(ra=ra[~missingi], dec=dec[~missingi], unit=uniti)
                except UnitTypeError as e:
                    info = e.args[0]
                    which_coor = self.ra_name if 'Longitude' in info else self.dec_name
                    got_unit =  info.split('set it to ')[-1]
                    raise UnitTypeError(f"Unrecognized unit for column '{which_coor}': expected units equivalent to 'rad', got {got_unit}"\
                                        f" Try manually setting {datai.__repr__()}.t['{which_coor}'].unit") from e
                except:
                    raise
            
            elif type(coordi) is SkyCoord:
                self.ra_name, self.dec_name = None, None
                coordi = coordi
                
                missingi = np.full(len(datai), False)
                not_missing_idi = np.arange(len(datai), dtype=int)[~missingi]
            
            else:
                raise TypeError(f"Unsupported type for coord/coord1: expected str or astropy.coordinates.SkyCoord, got {type(coordi)}")
                
            coords.append(coordi)
            missings.append(missingi)
            not_missing_ids.append(not_missing_idi)
        
        self.coord, self.coord1 = coords
        self.missing, self.missing1 = missings
        self.not_missing_id, self.not_missing_id1 = not_missing_ids
        
    def match(self):
        l = len(self.missing)
        idx = np.full(self.missing.shape, -l-1)
        matched = np.full(self.missing.shape, False)
        idx_nm, d2d, d3d = self.coord.match_to_catalog_sky(self.coord1)
        idx[~self.missing] = self.not_missing_id1[idx_nm]
        matched[~self.missing] = d2d.arcsec < self.thres
        return idx, matched
    
    def explore(self, data, data1):
        '''
        Plot as simple histogram to 
        check the distribution of the minimum (2-d) sky separation.

        Parameters
        ----------
        data : ``astrotable.table.Data``
            The base data of the match.
        data1 : ``astrotable.table.Data``
            The data to be matched to ``data1``.

        Returns
        -------
        None.

        '''
        self.get_values(data, data1)
        idx, d2d, d3d = self.coord.match_to_catalog_sky(self.coord1)
        import matplotlib.pyplot as plt
        plt.figure()
        plt.hist(np.log10(d2d.arcsec), bins=min((200, len(data)//20)), histtype='step', linewidth=1.5, log=True)
        plt.axvline(np.log10(self.thres), color='r', linestyle='--')
        plt.xlabel('lg (d / arcsec)')
        plt.title(f"Min. distance to '{data1.name}' objects for each '{data.name}' object\nthreshold={self.thres}\"")
        return d2d.arcsec
        
    def __repr__(self):
        return f'SkyMatcher with thres={self.thres}'
