from andes.core.model import Model, ModelData
from andes.core.param import NumParam, IdxParam, ExtParam
from andes.core.var import Algeb, ExtState, ExtAlgeb
from andes.core.service import ServiceConst, ExtService
from andes.core.discrete import HardLimiter, DeadBand
from andes.core.block import LeadLag


class TGBaseData(ModelData):
    def __init__(self):
        super().__init__()
        self.syn = IdxParam(model='SynGen', info='Synchronous generator idx', mandatory=True)
        self.R = NumParam(info='Speed regulation gain', tex_name='R', default=0.05, unit='pu')
        self.pmax = NumParam(info='Maximum power output', tex_name='p_{max}', power=True, default=999.0,
                             unit='pu')
        self.pmin = NumParam(info='Minimum power output', tex_name='p_{min}', power=True, default=0.0,
                             unit='pu')
        self.wref0 = NumParam(info='Base speed reference', tex_name=r'\omega_{ref0}', default=1.0,
                              unit='pu')
        self.dbl = NumParam(info='Deadband lower limit', tex_name='dbL', default=-0.0001,
                            unit='pu')
        self.dbu = NumParam(info='Deadband upper limit', tex_name='dbU', default=0.0001,
                            unit='pu')
        self.dbc = NumParam(info='Deadband neutral value', tex_name='dbC', default=0.0,
                            unit='pu')


class TGBase(Model):
    def __init__(self, system, config):
        Model.__init__(self, system, config)
        self.group = 'Governor'
        self.flags.update({'tds': True})
        self.config.add({'deadband': 0,
                         'hardlimit': 0})

        self.Sn = ExtParam(src='Sn', model='SynGen', indexer=self.syn, tex_name='S_m',
                           info='Rated power from generator', unit='MVA')
        self.pm0 = ExtService(src='pm', model='SynGen', indexer=self.syn, tex_name='p_{m0}')
        self.omega = ExtState(src='omega', model='SynGen', indexer=self.syn, tex_name=r'\omega',
                              info='Generator speed')
        self.pm = ExtAlgeb(src='pm', model='SynGen', indexer=self.syn, tex_name='P_m',
                           e_str='u*(pout - pm0)')
        self.pnl = Algeb(info='Power output before hard limiter', tex_name='P_{nl}',
                         v_init='pm0')
        self.pout = Algeb(info='Turbine power output after limiter', tex_name='P_{out}',
                          v_init='pm0')
        self.wref = Algeb(info='Speed referemce variable', tex_name=r'\omega_{ref}',
                          v_init='wref0', e_str='wref0 - wref')


class TG2Data(TGBaseData):
    def __init__(self):
        super().__init__()
        self.T1 = NumParam(info='Transient gain time', default=0.2)
        self.T2 = NumParam(info='Governor time constant', default=10.0)


class TG2(TG2Data, TGBase):
    def __init__(self, system, config):
        TG2Data.__init__(self)
        TGBase.__init__(self, system, config)
        self.tex_names = {'plim_zl': r'z_{P,l}',
                          'plim_zi': r'z_{P,i}',
                          'plim_zu': r'z_{P,u}',
                          'w_db_zl': 'z_{db,l}',
                          'w_db_zi': 'z_{db,i}',
                          'w_db_zu': 'z_{db,u}',
                          }
        self.T12 = ServiceConst(v_str='T1 / T2')
        self.gain = ServiceConst(v_str='u / R', tex_name='G')

        self.w_d = Algeb(info='Generator speed deviation before dead band (positive for under speed)',
                         tex_name=r'\omega_{dev}', v_init='0', e_str='(wref - omega) - w_d')
        self.w_dm = Algeb(info='Measured speed deviation after dead band', tex_name=r'\omega_{dm}',
                          v_init='0')
        self.w_db = DeadBand(var=self.w_dm, origin=self.w_d,
                             center=self.dbc, lower=self.dbl, upper=self.dbu,
                             enable=self.config.deadband)
        self.w_dm.e_str = '(1 - w_db_zi) * w_d + \
                            w_db_zlr * dbl + \
                            w_db_zur * dbu - \
                            w_dm'

        self.w_dmg = Algeb(info='Speed deviation after dead band after gain', tex_name=r'\omega_{dmG}',
                           v_init='0', e_str='gain * w_dm - w_dmg')
        self.leadlag = LeadLag(u=self.w_dmg, T1=self.T1, T2=self.T2)

        self.plim = HardLimiter(var=self.pout, origin=self.pnl, lower=self.pmin, upper=self.pmax,
                                enable=self.config.hardlimit)

        self.pnl.e_str = 'pm0 + leadlag_y - pnl'
        self.pout.e_str = 'pnl * plim_zi + pmax * plim_zu + pmin * plim_zl - pout'

# Developing a model (use TG2 as an example)
# 0) Find the group class or write a new group class in group.py
# 1) Determine and write the class `TG2Data` derived from ModelData
# 2) Write an empty class for the Model by inheriting `TG2Data` and `Model`
# 3) Implement the `__init__` function
#    a) Call parent class `__init__` methods.
#    b) Set `self.flags` for `pflow` and `tds` if applicable.
#    c) Define external service, algeb and states
#    d) Define base class variables and equations
# 4) Implement the TG2 class variables `pout` and add a limiter
